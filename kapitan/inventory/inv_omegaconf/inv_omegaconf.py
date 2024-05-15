#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import multiprocessing as mp
import os
from functools import singledispatch
from cachetools import cached, LRUCache
from omegaconf import OmegaConf
from ..inventory import InventoryError, Inventory, InventoryTarget
from .resolvers import register_resolvers
from kadet import Dict
from .migrate import migrate
import yaml

logger = logging.getLogger(__name__)

@singledispatch
def keys_to_strings(ob):
    return ob


@keys_to_strings.register
def _handle_dict(ob: dict):
    return {str(k): keys_to_strings(v) for k, v in ob.items()}


@keys_to_strings.register
def _handle_list(ob: list):
    return [keys_to_strings(v) for v in ob]

 
class OmegaConfTarget(InventoryTarget):
    resolved: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__add_metadata()
        
    def resolve(self):
        if not self.resolved:
            parameters = self.parameters
            if isinstance(parameters, Dict):
                parameters = parameters.to_dict()
                parameters = OmegaConf.create(keys_to_strings(parameters))

            self.parameters = OmegaConf.to_container(parameters, resolve=True)
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
    def resolve_class_file_path(self, class_name: str, class_parent_dir: str = None, class_parent_name: str = None):
        class_file = None
       
        # Finds relative paths based on the parent directory 
        if class_name.startswith(".") and class_parent_dir:
            class_path_base = os.path.join(self.classes_path, class_parent_dir)
        else:
            class_path_base = self.classes_path
             
        # Now try to find the class file
        extension = ".yml"
        
        cases = [
            # case components.kapicorp is absolute and a directory, look for components/kapicorp/init.yml
            # case .components.kapicorp is relative and a directory, look for <class_parent_dir>/components/kapicorp/init.yml
            os.path.join(class_path_base, *class_name.split("."), "init" + extension),
            
            # case components.kapicorp is absolute and a file, look for components/kapicorp.yml
            # case components.kapicorp is relative and a file, look for <class_parent_dir>/components/kapicorp.yml
            os.path.join(class_path_base, *class_name.split(".")) + extension,
            
            # Reclass compatibility mode
            # case .components.kapicorp  points to <class_parent_dir>/kapicorp.yml
            os.path.join(class_path_base, *class_name.split(".")[2:]) + extension,
            
            # case components.kapicorp points to components/kapicorp/init.yml
            os.path.join(class_path_base, *class_name.split(".")[2:], "init" + extension),
        ]
        
        for case in cases:
            if os.path.isfile(case):
                class_file = case
                return class_file
            
        logger.error(f"class file not found for class {class_name}, tried {cases}")
        return None

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
            class_parent_name = os.path.basename(filename)
            class_file = self.resolve_class_file_path(class_name, class_parent_dir=class_parent_dir, class_parent_name=class_parent_name)
            if not class_file:
                if self.ignore_class_not_found:
                    continue
                raise InventoryError(f"Class {class_name} not found")
            p, c, a, e = self.load_parameters_from_file(class_file)
            parameters.merge_update(p, box_merge_lists="unique")
            classes.extend(c)
            applications.extend(a)
            exports.merge_update(e, box_merge_lists="unique")
        
        # finally merges the parameters from the current file
        parameters.merge_update(_parameters, box_merge_lists="unique")
        classes.extend(_classes)
        exports.merge_update(_exports, box_merge_lists="unique")
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