#!/usr/bin/env python3

# Copyright 2023 The Kapitan Authors
# SPDX-FileCopyrightText: 2023 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from abc import ABC, abstractmethod
from pydantic import BaseModel
from kapitan.errors import KapitanError

logger = logging.getLogger(__name__)


class InventoryTarget(BaseModel):
    name: str
    path: str
    parameters: dict = dict()
    classes: list = list()
    applications: list = list()
    exports: list = list()


class Inventory(ABC):
    _default_path: str = "inventory"

    def __init__(self, inventory_path: str = _default_path, compose_target_name: bool = False):
        self.inventory_path = inventory_path
        self.targets_path = os.path.join(inventory_path, "targets")
        self.classes_path = os.path.join(inventory_path, "classes")

        # config
        self.compose_target_name = compose_target_name

        self.targets = {}

    @property
    def inventory(self) -> dict:
        """
        get all targets from inventory
        targets will be rendered
        """

        return {
            target.name: {"parameters": target.parameters, "classes": target.classes}
            for target in self.get_targets().values()
        }

    def search_targets(self) -> dict:
        """
        look for targets at '<inventory_path>/targets/' and return targets without rendering parameters
        """
        
        for root, dirs, files in os.walk(self.targets_path):
            for file in files:
                # split file extension and check if yml/yaml
                path = os.path.relpath(os.path.join(root, file), self.targets_path)

                if self.compose_target_name:
                    name, ext = os.path.splitext(path)
                    name = name.replace(os.sep, ".")
                else:
                    name, ext = os.path.splitext(file)
                    
                if ext not in (".yml", ".yaml"):
                    logger.debug(f"ignoring {file}: targets have to be .yml or .yaml files.")
                    continue

                target = InventoryTarget(name=name, path=path)



                if self.targets.get(target.name):
                    raise InventoryError(
                        f"Conflicting targets {target.name}: {target.path} and {self.targets[target.name].path}. "
                        f"Consider using '--compose-target-name'."
                    )
                
                self.targets[target.name] = target
        return self.targets

    def get_target(self, target_name: str, ignore_class_not_found: bool = False) -> InventoryTarget:
        """
        helper function to get rendered InventoryTarget object for single target
        """
        return self.get_targets([target_name], ignore_class_not_found)[target_name]

    def get_targets(self, target_names: list[str] = [], ignore_class_not_found: bool = False) -> dict:
        """
        helper function to get rendered InventoryTarget objects for multiple targets
        """
        if not self.targets:
            self.search_targets()
            
        targets_to_render = []
        targets = {}
        
        if not target_names:
            targets = self.targets
        else:
            try:
                targets = { target_name : self.targets[target_name] for target_name in target_names }
            except KeyError as e:
                if not ignore_class_not_found:
                    raise InventoryError(f"targets not found: {set(target_names)-set(self.targets)}" )

        for target in targets.values():
            if not target.parameters:
                targets_to_render.append(target)

        if targets_to_render:
            self.render_targets(targets_to_render, ignore_class_not_found)

        return self.targets

    def get_parameters(self, target_names: str | list[str], ignore_class_not_found: bool = False) -> dict:
        """
        helper function to get rendered parameters for single target or multiple targets
        """
        if type(target_names) is str:
            target = self.get_target(target_names, ignore_class_not_found)
            return target.parameters

        return {name: target.parameters for name, target in self.get_targets(target_names)}

    @abstractmethod
    def render_targets(self, targets: list[InventoryTarget] = None, ignore_class_notfound: bool = False) -> None:
        """
        create the inventory depending on which backend gets used
        """
        raise NotImplementedError

    def migrate(self):
        """
        migrate the inventory, e.g. change interpolation syntax to new syntax
        """
        pass

    def __getitem__(self, key):
        return self.inventory[key]


class InventoryError(KapitanError):
    """inventory error"""

    pass


class InventoryValidationError(InventoryError):
    """inventory validation error"""

    pass


class InvalidTargetError(InventoryError):
    """inventory validation error"""

    pass
