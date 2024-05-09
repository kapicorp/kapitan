#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import multiprocessing as mp
import os
from cachetools import cached, LRUCache
from omegaconf import OmegaConf

from typing import Self
from ..inventory import InventoryError, Inventory, InventoryTarget
from .resolvers import register_resolvers
from kadet import Dict


logger = logging.getLogger(__name__)


class OmegaConfTarget(InventoryTarget):
    resolved: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__add_metadata()
        
    def resolve(self) -> Self:
        if not self.resolved:
            parameters = self.parameters
            if isinstance(parameters, Dict):
                parameters = OmegaConf.create(parameters.to_dict())
            elif isinstance(parameters, dict):
                parameters = OmegaConf.create(parameters)
            OmegaConf.resolve(parameters, escape_interpolation_strings=False)

            self.parameters = Dict(OmegaConf.to_container(parameters)).to_dict()
            self.resolved = True
        return self

    def __add_metadata(self):
        metadata = {
            "name": {
                "short": self.name.split(".")[-1],
                "full": self.name,
                "path": self.path,
                "parts": self.name.split("."),
            }
        }
        self.parameters["_kapitan_"] = metadata
        self.parameters["_reclass_"] = metadata


class OmegaConfInventory(Inventory):
    classes_cache: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, target_class=OmegaConfTarget)
   
    def render_targets(self, targets: list[OmegaConfTarget] = None, ignore_class_not_found: bool = False) -> None:
        manager = mp.Manager()
        shared_targets = manager.dict()
        mp.set_start_method("spawn", True)  # platform independent
        with mp.Pool(min(len(targets), os.cpu_count())) as pool:
            r = pool.map_async(self.inventory_worker, [(self, target, shared_targets) for target in targets.values()])
            r.wait()
        
        for target in shared_targets.values():
            self.targets[target.name] = target
        
    @staticmethod
    def inventory_worker(zipped_args):
        self, target, shared_targets = zipped_args
        try:
            self.load_target(target)
            register_resolvers(self.inventory_path)
            target.resolve()
            shared_targets[target.name] = target
            
        except Exception as e:
            logger.error(f"{target.name}: could not render due to error {e}")
            raise

    @cached(cache=LRUCache(maxsize=1024))
    def resolve_class_file_path(self, class_name: str, class_parent_dir: str = None):
        class_file = None
        
        if class_name.startswith(".") and class_parent_dir:
            class_name = class_parent_dir + class_name
        
        class_path_base = os.path.join(self.classes_path, *class_name.split("."))
        
        if os.path.isfile(os.path.join(class_path_base, "init.yml")):
            class_file = os.path.join(class_path_base, "init.yml")
        elif os.path.isfile(class_path_base + ".yml"):
            class_file = f"{class_path_base}.yml"
            
        return class_file

    @cached(cache=LRUCache(maxsize=1024))
    def load_file(self, filename):
        return Dict.from_yaml(filename=filename)
        
    @cached(cache=LRUCache(maxsize=1024))
    def load_parameters_from_file(self, filename, parameters={}) -> Dict:
        parameters = Dict(parameters)
        content = self.load_file(filename)
        
        _classes = content.get("classes", [])
        _parameters = content.get("parameters", {})

        # first processes all classes 
        for class_name in _classes:
            class_parent_dir = os.path.dirname(filename.removeprefix(self.classes_path).removeprefix("/"))
            class_file = self.resolve_class_file_path(class_name, class_parent_dir=class_parent_dir)
            if not class_file:
                if self.ignore_class_not_found:
                    continue
                raise InventoryError(f"Class {class_name} not found")
            parameters.merge_update(self.load_parameters_from_file(class_file), box_merge_lists="extend")
        
        # finally merges the parameters from the current file
        parameters.merge_update(_parameters, box_merge_lists="extend")
        return parameters
     
    def load_target(self, target: OmegaConfTarget):
        full_target_path = os.path.join(self.targets_path, target.path)
        
        parameters = Dict(target.parameters, frozen_box=True)
        target.parameters = self.load_parameters_from_file(full_target_path, parameters=parameters).to_dict()
        
    def resolve_all_target(self):
        map(lambda x: x.resolve(), self.targets)