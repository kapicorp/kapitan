#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import unittest
import logging
import tempfile
import shutil
import os

logger = logging.getLogger(__name__)

TEST_PWD = os.getcwd()
TEST_KUBERNETES_INVENTORY = os.path.join(TEST_PWD, "examples/kubernetes/")

from kapitan.inventory.inv_omegaconf.inv_omegaconf import OmegaConfInventory as inventory_backend

class InventoryTestOmegaConf(unittest.TestCase):
    temp_dir = tempfile.mkdtemp()
    
    def setUp(self) -> None:
        shutil.copytree(TEST_KUBERNETES_INVENTORY, self.temp_dir, dirs_exist_ok=True)
        self.inventory_path = self.temp_dir
        self.extraArgv = ["--inventory-backend=omegaconf"]
        from kapitan.inventory.inv_omegaconf import migrate
        inventory_path = os.path.join(self.temp_dir, "inventory")
        migrate.migrate(inventory_path)
        self.inventory_backend = inventory_backend(inventory_path=inventory_path, initialise=False) 

    def test_load_and_resolve_single_target(self):
        target_name = "minikube"
        target_kapitan_metadata = dict({'_kapitan_': {'name': {'short': 'minikube', 'full': 'minikube', 'path': 'minikube-es', 'parts': ['minikube']}}})
        
        # Load inventory but does not initialises targets
        inventory = self.inventory_backend
        
        # Manually create a new Target
        target = inventory.target_class(name=target_name, path="minikube-es.yml")
        
        # Adds target to Inventory
        inventory.targets.update({target_name: target})
        
        # Loads the target using the inventory
        inventory.load_target(target)

        self.assertDictEqual(target_kapitan_metadata["_kapitan_"], target.parameters["_kapitan_"])
        self.assertEqual(target.parameters["_kapitan_"]["name"]["short"], "minikube")
        self.assertEqual(target.parameters["target_name"], "minikube-es")
        self.assertEqual(target.parameters["kubectl"]["insecure_skip_tls_verify"], False)
        
    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
        return super().tearDown()