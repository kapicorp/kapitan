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
from ..inventory import InventoryError, Inventory, InventoryTarget
from .resolvers import register_resolvers
from kadet import Dict
from .migrate import migrate
import yaml

logger = logging.getLogger(__name__)

   
class OmegaConfTarget(InventoryTarget):
    resolved: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__add_metadata()
        
    def resolve(self):
        if not self.resolved:
            parameters = self.parameters
            if isinstance(parameters, Dict):
                parameters = OmegaConf.create(parameters.to_dict())
            elif isinstance(parameters, dict):
                parameters = OmegaConf.create(parameters)
            OmegaConf.resolve(parameters, escape_interpolation_strings=False)

            self.parameters = OmegaConf.to_container(parameters)
            self.resolved = True
        return self

    def __add_metadata(self):
        metadata = {
            "name": {
                "short": self.name.split(".")[-1],
                "full": self.name,
                "path": os.path.splitext(self.path)[0],
                "parts": self.name.split("."),
            }
        }
        self.parameters["_kapitan_"] = metadata
        self.parameters["_reclass_"] = metadata


class OmegaConfInventory(Inventory):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, target_class=OmegaConfTarget)
   
    def render_targets(self, targets: list[OmegaConfTarget] = None, ignore_class_not_found: bool = False) -> None:
        if not self.initialised:
            manager = mp.Manager()
            shared_targets = manager.dict()
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
        with open(filename, "r") as f:
            return yaml.safe_load(f)
        
    def load_parameters_from_file(self, filename, parameters={}) -> Dict:
        parameters = Dict(parameters)
        applications = []
        classes = []
        exports = Dict()
        
        content = self.load_file(filename)
        
        _classes = content.get("classes", [])
        _parameters = content.get("parameters", {})
        _applications = content.get("applications", [])
        _exports = content.get("exports", Dict())

        # first processes all classes 
        for class_name in _classes:
            class_parent_dir = os.path.dirname(filename.removeprefix(self.classes_path).removeprefix("/"))
            class_file = self.resolve_class_file_path(class_name, class_parent_dir=class_parent_dir)
            if not class_file:
                if self.ignore_class_not_found:
                    continue
                raise InventoryError(f"Class {class_name} not found")
            p, c, a, e = self.load_parameters_from_file(class_file)
            parameters.merge_update(p, box_merge_lists="extend")
            classes.extend(c)
            applications.extend(a)
            exports.merge_update(e, box_merge_lists="extend")
        
        # finally merges the parameters from the current file
        parameters.merge_update(_parameters, box_merge_lists="extend")
        classes.extend(_classes)
        exports.merge_update(_exports, box_merge_lists="extend")
        applications.extend(_applications)
        return parameters, classes, applications, exports
     
    def load_target(self, target: OmegaConfTarget):
        full_target_path = os.path.join(self.targets_path, target.path)
        
        parameters = Dict(target.parameters, frozen_box=True)
        p, c, a, e = self.load_parameters_from_file(full_target_path, parameters=parameters)
        target.parameters = p
        target.classes = c
        target.applications = a
        target.exports = e
    
    def migrate(self):
        migrate(self.inventory_path)
        
    def resolve_targets(self, targets: list[OmegaConfTarget] = None) -> None:
        if not targets:
            targets = self.targets.values()
        map(lambda target: target.resolve(), targets)