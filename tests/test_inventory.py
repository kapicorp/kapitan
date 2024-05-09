#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import importlib
import unittest
import logging

logger = logging.getLogger(__name__)

from kapitan.cached import reset_cache, args
from kapitan.resources import inventory

reset_cache()


class InventoryTargetTestBase(unittest.TestCase):
    def setUp(self) -> None:
        reset_cache()
        if not importlib.util.find_spec(self.backend_id):
            self.skipTest(f"backend module {self.backend_id} not available")

        self.inventory_path = "examples/kubernetes/inventory"
        
        args.inventory_backend = self.backend_id 
        
    def test_inventory_target(self):
        inv = inventory(inventory_path=self.inventory_path, target_name="minikube-es")
        logger.error(inv)
        self.assertEqual(inv["parameters"]["cluster"]["name"], "minikube")

    def test_inventory_all_targets(self):
        inv = inventory(inventory_path=self.inventory_path)
        self.assertNotEqual(inv.get("minikube-es"), None)
        self.assertEqual(len(inv), self.expected_targets_count)


class InventoryTargetTestReclass(InventoryTargetTestBase):
    def setUp(self):
        self.backend_id = "reclass"
        self.expected_targets_count = 10
        super().setUp()


class InventoryTargetTestReclassRs(InventoryTargetTestBase):
    def setUp(self):
        self.backend_id = "reclass_rs"
        self.expected_targets_count = 10
        super().setUp()


class InventoryTargetTestOmegaConf(InventoryTargetTestBase):
    def setUp(self):
        self.backend_id = "omegaconf"
        self.expected_targets_count = 1
        super().setUp()
        
        self.inventory_path = "tests/test_omegaconf_inventory"





del (InventoryTargetTestBase)  # remove InventoryTargetTestBase so that it doesn't run