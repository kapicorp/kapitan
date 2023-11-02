#!/usr/bin/env python3

# Copyright 2023 The Kapitan Authors
# SPDX-FileCopyrightText: 2023 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod

from kapitan.errors import InventoryError


class Inventory(ABC):
    _instance: object

    def __new__(cls, *args, **kwargs):
        """
        create only one specific inventory instance (singleton)
        """
        if not cls._instance:
            # initialize new instance
            cls._instance = super(Inventory, cls).__new__(cls)
            cls._instance.__init__(**args, **kwargs)
        return cls._instance

    def __init__(self, inventory_path: str, compose_node_name: dict = False):
        self.inventory_path = inventory_path
        self.compose_node_name = compose_node_name
        self._parameters = None

    @property
    def inventory(self) -> dict:
        if not self._parameters:
            self._parameters = self.get_parameters()
        return self._parameters

    @abstractmethod
    def get_parameters(self, ignore_class_notfound=False) -> dict:
        """
        create the inventory depending which backend gets used
        """
        raise NotImplementedError

    def search_targets(self) -> list:
        """
        look for targets at '<inventory_path>/targets/'
        """
        targets = []
        return targets

    def get_target(self, target_name: str) -> dict:
        """
        get parameters for a specific target
        """
        target = self.inventory.get(target_name)
        if not target:
            raise InventoryError(f"target '{target_name}' not found")
        return target

    def fetch_dependencies(self):
        raise NotImplementedError
