#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import unittest
import logging

logger = logging.getLogger(__name__)

from kapitan.inventory.inv_omegaconf.inv_omegaconf import OmegaConfInventory as inventory_backend

class InventoryTestOmegaconf(unittest.TestCase):
    
    def setUp(self) -> None:
        self.inventory_path = "tests/test_omegaconf_inventory"
        self.inventory_backend = inventory_backend(inventory_path=self.inventory_path, initialise=False) 
        return super().setUp()

    def test_load_and_resolve_single_target(self):
        target_name = "minikube"
        target_kapitan_metadata = {'_kapitan_': {'name': {'short': 'minikube', 'full': 'minikube', 'path': 'minikube-es.yml', 'parts': ['minikube']}}}
        
        # Load inventory but does not initialises targets
        inventory = self.inventory_backend
        
        # Manually create a new Target
        target = inventory.target_class(name=target_name, path="minikube-es.yml")
        
        # Adds target to Inventory
        inventory.targets.update({target_name: target})
        
        # Loads the target using the inventory
        inventory.load_target(target)

        self.assertDictContainsSubset(target_kapitan_metadata, target.parameters)
        self.assertEqual(target.parameters["_kapitan_"]["name"]["short"], "minikube")
        self.assertEqual(target.parameters["target_name"], "minikube-es")
        self.assertEqual(target.parameters["uninterpolated"], "${.target_name}")
        self.assertEqual(target.parameters["kubectl"]["insecure_skip_tls_verify"], False)
        
        resolved = target.resolve().parameters
        self.assertEqual(resolved["uninterpolated"], "minikube-es")
