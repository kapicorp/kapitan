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
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        create only one specific inventory instance (singleton)
        """
        if Inventory._instance is None:
            Inventory._instance = super().__new__(cls)
        return Inventory._instance

    def __init__(self, inventory_path: str, compose_node_name: dict = False):
        self.inventory_path = inventory_path
        self.targets_path = os.path.join(inventory_path, "targets")
        self.classes_path = os.path.join(inventory_path, "classes")

        # config
        self.compose_node_name = compose_node_name

        # used as cache for inventory
        self._targets = {}
        self._parameters = {}

    @classmethod
    def get(cls):
        if cls._instance is None:
            raise InventoryError("no type specified")
        return cls._instance

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

    def fetch_dependencies(self, fetch, force_fetch):
        # fetch inventory
        if fetch:
            # new_source checks for new sources in fetched inventory items
            new_sources = list(set(list_sources(target_objs)) - cached.inv_sources)
            while new_sources:
                fetch_inventories(
                    inventory_path,
                    target_objs,
                    dep_cache_dir,
                    force_fetch,
                    pool,
                )
                cached.reset_inv()
                target_objs = load_target_inventory(updated_targets)
                cached.inv_sources.update(new_sources)
                new_sources = list(set(list_sources(target_objs)) - cached.inv_sources)
            # reset inventory cache and load target objs to check for missing classes
            cached.reset_inv()
            target_objs = load_target_inventory(updated_targets)
        # fetch dependencies
        if fetch:
            fetch_dependencies(output_path, target_objs, dep_cache_dir, force_fetch, pool)
        # fetch targets which have force_fetch: true
        elif not kwargs.get("force_fetch", False):
            fetch_objs = []
            # iterate through targets
            for target in target_objs:
                try:
                    # get value of "force_fetch" property
                    dependencies = target["dependencies"]
                    # dependencies is still a list
                    for entry in dependencies:
                        force_fetch = entry["force_fetch"]
                        if force_fetch:
                            fetch_objs.append(target)
                except KeyError:
                    # targets may have no "dependencies" or "force_fetch" key
                    continue
            # fetch dependencies from targets with force_fetch set to true
            if fetch_objs:
                fetch_dependencies(output_path, fetch_objs, dep_cache_dir, True, pool)


class InventoryError(KapitanError):
    """inventory error"""

    pass


class InventoryValidationError(InventoryError):
    """inventory validation error"""

    pass
