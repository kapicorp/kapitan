#!/usr/bin/env python3

# Copyright 2023 The Kapitan Authors
# SPDX-FileCopyrightText: 2023 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import overload, Union

from kapitan.errors import KapitanError
from kapitan.reclass.reclass.values import item

logger = logging.getLogger(__name__)


@dataclass
class InventoryTarget:
    name: str
    path: str
    composed_name: str
    parameters: dict = field(default_factory=dict)
    classes: list = field(default_factory=list)


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
        if not self.targets:
            self.search_targets()

        inventory = self.get_targets([*self.targets.keys()])

        return {
            target_name: {"parameters": target.parameters, "classes": target.classes}
            for target_name, target in inventory.items()
        }

    def search_targets(self) -> dict:
        """
        look for targets at '<inventory_path>/targets/' and return targets without rendering parameters
        """
        for root, dirs, files in os.walk(self.targets_path):
            for file in files:
                # split file extension and check if yml/yaml
                path = os.path.join(root, file)
                name, ext = os.path.splitext(file)
                if ext not in (".yml", ".yaml"):
                    logger.debug(f"{file}: targets have to be .yml or .yaml files.")
                    continue

                # initialize target
                composed_name = (
                    os.path.splitext(os.path.relpath(path, self.targets_path))[0]
                    .replace(os.sep, ".")
                    .lstrip(".")
                )
                target = InventoryTarget(name, path, composed_name)
                if self.compose_target_name:
                    target.name = target.composed_name

                # check for same name
                if self.targets.get(target.name):
                    raise InventoryError(
                        f"Conflicting targets {target.name}: {target.path} and {self.targets[target.name].path}"
                    )

                self.targets[target.name] = target

        return self.targets

    def get_target(self, target_name: str, ignore_class_not_found: bool = False) -> InventoryTarget:
        """
        helper function to get rendered InventoryTarget object for single target
        """
        return self.get_targets([target_name], ignore_class_not_found)[target_name]

    def get_targets(self, target_names: list, ignore_class_not_found: bool = False) -> dict:
        """
        helper function to get rendered InventoryTarget objects for multiple targets
        """
        targets_to_render = []

        for target_name in target_names:
            target = self.targets.get(target_name)
            if not target:
                if ignore_class_not_found:
                    continue
                raise InventoryError(f"target '{target_name}' not found")

            if not target.parameters:
                targets_to_render.append(target)

        self.render_targets(targets_to_render, ignore_class_not_found)

        return {name: target for name, target in self.targets.items() if name in target_names}

    def get_parameters(self, target_names: Union[str, list], ignore_class_not_found: bool = False) -> dict:
        """
        helper function to get rendered parameters for single target or multiple targets
        """
        if type(target_names) is str:
            target = self.get_target(target_names, ignore_class_not_found)
            return target.parameters

        return {name: target.parameters for name, target in self.get_targets(target_names)}

    @abstractmethod
    def render_targets(self, targets: list = None, ignore_class_notfound: bool = False):
        """
        create the inventory depending on which backend gets used
        """
        raise NotImplementedError

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
