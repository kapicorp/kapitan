#!/usr/bin/env python3

# Copyright 2023 The Kapitan Authors
# SPDX-FileCopyrightText: 2023 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from kapitan import cached
from kapitan.errors import InventoryError, KapitanError

logger = logging.getLogger(__name__)


@dataclass
class InventoryTarget(dict):
    targets_path: str

    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path

        # compose node name
        self.composed_name = os.path.splitext(path)[0].replace(path + os.sep, "").replace("/", ".")

    @property
    def kapitan(self) -> dict():
        kapitan_spec = self.get("kapitan")
        if not kapitan_spec:
            raise InventoryValidationError("parameters.kapitan is empty")

        return kapitan_spec

    @property
    def parameters(self) -> dict():
        parameters = self.get("parameters")
        if not parameters:
            raise InventoryValidationError("parameters is empty")

        return parameters


class Inventory(ABC):
    def __init__(self, inventory_path: str, ignore_class_not_found: bool = False):
        self.inventory_path = inventory_path
        self.targets_path = os.path.join(inventory_path, "targets")
        self.classes_path = os.path.join(inventory_path, "classes")

        # config
        # self.compose_node_name = compose_node_name

        # used as cache for inventory
        self._targets = {}
        self._parameters = {}

    @property
    def inventory(self) -> dict:
        if not self._parameters:
            self._parameters = self.get_parameters()
            cached.inv = self._parameters
        return self._parameters

    @abstractmethod
    def get_parameters(self, ignore_class_notfound: bool = False) -> dict:
        """
        create the inventory depending which backend gets used
        """
        raise NotImplementedError

    def search_targets(self) -> dict:
        """
        look for targets at '<inventory_path>/targets/' and return targets
        """
        for root, _, files in os.walk(self.targets_path):
            for file in files:
                # split file extension and check if yml/yaml
                path = os.path.join(root, file)
                name, ext = os.path.splitext(file)
                if ext not in (".yml", ".yaml"):
                    logger.debug(f"{file}: targets have to be .yml or .yaml files.")
                    continue

                # initialize target
                target = InventoryTarget(name, path)
                if self.compose_node_name:
                    target.name = target.composed_name

                # check for same name
                if self._targets.get(target.name):
                    raise InventoryError(
                        f"Conflicting targets {target.name}: {target.path} and {self._targets[target.name].path}"
                    )

                self._targets[target.name] = target

        return self._targets

    def get_target(self, target_name: str) -> dict:
        """
        get parameters for a specific target
        """
        return self.get_targets([target_name])

    @abstractmethod
    def get_targets(self, target_names: list[str]) -> dict:
        """
        get parameters for multiple targets
        """
        raise NotImplementedError


class InventoryError(KapitanError):
    """inventory error"""

    pass


class InventoryValidationError(InventoryError):
    """inventory validation error"""

    pass
