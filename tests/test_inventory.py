#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import importlib
import unittest
import logging
import tempfile
import os
import shutil
logger = logging.getLogger(__name__)

from kapitan.resources import inventory

TEST_PWD = os.getcwd()
TEST_KUBERNETES_INVENTORY = os.path.join(TEST_PWD, "examples/kubernetes/")


class InventoryTargetTestBase(unittest.TestCase):
    
    def setUp(self) -> None:
        from kapitan.cached import reset_cache, args
        
        reset_cache()
        if not importlib.util.find_spec(self.backend_id):
            self.skipTest(f"backend module {self.backend_id} not available")
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
        self.inventory_path = "examples/kubernetes/inventory"
        super().setUp()


class InventoryTargetTestReclassRs(InventoryTargetTestBase):
    def setUp(self):
        self.backend_id = "reclass_rs"
        self.expected_targets_count = 10
        self.inventory_path = "examples/kubernetes/inventory"
        super().setUp()


class InventoryTargetTestOmegaConf(InventoryTargetTestBase):
    temp_dir = tempfile.mkdtemp()

    def setUp(self) -> None:
        shutil.copytree(TEST_KUBERNETES_INVENTORY, self.temp_dir, dirs_exist_ok=True)
        self.backend_id = "omegaconf"
        self.expected_targets_count = 10
        from kapitan.inventory.inv_omegaconf import migrate
        self.inventory_path = os.path.join(self.temp_dir, "inventory")
        migrate.migrate(self.inventory_path)
        super().setUp()
    
    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
        return super().tearDown()


del (InventoryTargetTestBase)  # remove InventoryTargetTestBase so that it doesn't run