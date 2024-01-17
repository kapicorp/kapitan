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

from kapitan.errors import KapitanError
from kapitan.reclass.reclass.values import item

logger = logging.getLogger(__name__)


@dataclass
class InventoryTarget:
    name: str
    path: str
    composed_name: str
    parameters: dict = field(default_factory=dict)


class Inventory(ABC):
    path: str = "inventory"

    def __init__(self, path: str = path, compose_target_name: bool = False):
        self.inventory_path = path
        self.targets_path = os.path.join(path, "targets")
        self.classes_path = os.path.join(path, "classes")

        # config
        self.compose_target_name = compose_target_name

        self.targets = {}

    @property
    def inventory(self) -> dict:
        if not self.targets:
            return self.render_targets()
        return {name: target.parameters for name, target in self.targets.items()}

    @abstractmethod
    def render_targets(self, targets: list = None, ignore_class_notfound: bool = False) -> dict:
        """
        create the inventory depending on which backend gets used
        """
        raise NotImplementedError

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

    def get_target(self, target_name: str) -> dict:
        """
        helper function to get parameters for a specific target
        """
        return self.get_targets([target_name])[target_name]

    @abstractmethod
    def get_targets(self, target_names: list[str]) -> dict:
        """
        helper function to get parameters for multiple targets
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
