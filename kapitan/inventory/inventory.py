#!/usr/bin/env python3

# Copyright 2023 The Kapitan Authors
# SPDX-FileCopyrightText: 2023 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import functools
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field

from kapitan.errors import KapitanError
from kapitan.inventory.model import KapitanInventoryParameters

logger = logging.getLogger(__name__)


class InventoryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    name: str = Field(exclude=True)
    path: str = Field(exclude=True)
    parameters: KapitanInventoryParameters = KapitanInventoryParameters()
    classes: list = list()
    applications: list = list()
    exports: dict = {}


class Inventory(ABC):
    def __init__(
        self,
        inventory_path: str = "inventory",
        compose_target_name: bool = False,
        ignore_class_not_found=False,
        initialise=True,
        target_class=InventoryTarget,
    ):
        self.inventory_path = inventory_path
        self.compose_target_name = compose_target_name
        self.targets_path = os.path.join(self.inventory_path, "targets")
        self.classes_path = os.path.join(self.inventory_path, "classes")
        self.initialised: bool = False
        self.targets: dict[str, target_class] = {}
        self.ignore_class_not_found = ignore_class_not_found
        self.target_class = target_class

        if initialise:
            self.__initialise(ignore_class_not_found=ignore_class_not_found)

    @functools.cached_property
    def inventory(self) -> dict:
        """
        get all targets from inventory
        """

        return {target.name: target.model_dump(by_alias=True) for target in self.targets.values()}

    def __initialise(self, ignore_class_not_found) -> bool:
        """
        look for targets at '<inventory_path>/targets/' and initialise them.
        """
        logger.debug(f"Initialising inventory from {self.targets_path}")
        if not self.initialised:
            for root, _, files in os.walk(self.targets_path):
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

                    target = self.target_class(name=name, path=path)

                    if self.targets.get(target.name):
                        raise InventoryError(
                            f"Conflicting targets {target.name}: {target.path} and {self.targets[target.name].path}. "
                            f"Consider using '--compose-target-name'."
                        )

                    self.targets[target.name] = target

            self.render_targets(self.targets, ignore_class_not_found=ignore_class_not_found)
            self.initialised = True
        return self.initialised

    def get_target(self, target_name: str, ignore_class_not_found: bool = False) -> InventoryTarget:
        """
        helper function to get rendered InventoryTarget object for single target
        """
        return self.targets.get(target_name)

    def get_targets(self, target_names: list[str] = [], ignore_class_not_found: bool = False) -> dict:
        """
        helper function to get rendered InventoryTarget objects for multiple targets
        """

        if target_names:
            return {
                target_name: self.targets[target_name]
                for target_name in target_names
                if target_name in self.targets
            }
        else:
            return self.targets

    def get_parameters(self, target_names: str | list[str], ignore_class_not_found: bool = False) -> dict:
        """
        helper function to get rendered parameters for single target or multiple targets
        """
        if type(target_names) is str:
            target = self.get_target(target_names, ignore_class_not_found)
            return target.parameters

        return {
            name: {"parameters": Dict(target.parameters)} for name, target in self.get_targets(target_names)
        }

    @abstractmethod
    def render_targets(
        self, targets: list[InventoryTarget] = None, ignore_class_not_found: bool = False
    ) -> None:
        """
        create the inventory depending on which backend gets used
        """
        raise NotImplementedError

    def migrate(self):
        """
        migrate the inventory, e.g. change interpolation syntax to new syntax
        """

    def __getitem__(self, key):
        return self.inventory[key]


class InventoryError(KapitanError):
    """inventory error"""


class InventoryValidationError(InventoryError):
    """inventory validation error"""


class InvalidTargetError(InventoryError):
    """inventory validation error"""
