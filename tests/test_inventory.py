#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import importlib
import logging
import os
import shutil
import sys
import tempfile
import unittest

import kapitan.cached
from kapitan.cli import build_parser
from kapitan.inventory import InventoryBackends
from kapitan.resources import inventory


logger = logging.getLogger(__name__)


TEST_PWD = os.getcwd()
TEST_KUBERNETES_INVENTORY = os.path.join(TEST_PWD, "examples/kubernetes/")


class InventoryTargetTestBase(unittest.TestCase):
    backend_id = None
    inventory_path = None
    expected_targets_count = None

    def setUp(self) -> None:
        sys.argv = ["kapitan", "compile"]
        args = build_parser().parse_args()

        # Fix inconsistency between reclass-rs (option name) and reclass_rs (module name)
        backend_module_name = self.backend_id.replace("-", "_")
        if not importlib.util.find_spec(backend_module_name):
            self.skipTest(f"backend module {backend_module_name} not available")
        args.inventory_backend = self.backend_id
        kapitan.cached.args = args

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
        self.backend_id = InventoryBackends.RECLASS
        self.expected_targets_count = 10
        self.inventory_path = "examples/kubernetes/inventory"
        super().setUp()


class InventoryTargetTestReclassRs(InventoryTargetTestBase):
    def setUp(self):
        self.backend_id = InventoryBackends.RECLASS_RS
        self.expected_targets_count = 10
        self.inventory_path = "examples/kubernetes/inventory"
        super().setUp()


class InventoryTargetTestOmegaConf(InventoryTargetTestBase):
    temp_dir = tempfile.mkdtemp()

    def setUp(self) -> None:
        shutil.copytree(TEST_KUBERNETES_INVENTORY, self.temp_dir, dirs_exist_ok=True)
        self.backend_id = InventoryBackends.OMEGACONF
        self.expected_targets_count = 10
        from kapitan.inventory.backends.omegaconf import migrate

        self.inventory_path = os.path.join(self.temp_dir, "inventory")
        migrate(self.inventory_path)
        super().setUp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
        return super().tearDown()


TEST_RESOURCES_OC_INVENTORY = os.path.join(
    TEST_PWD, "tests/test_resources_oc/inventory"
)


class InventoryTargetTestOmegaConfOC(unittest.TestCase):
    """Test inventory with test_resources_oc using omegaconf backend (deferred resolvers)."""

    def setUp(self) -> None:
        from omegaconf import OmegaConf

        from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers

        self.backend_id = InventoryBackends.OMEGACONF
        self.inventory_path = TEST_RESOURCES_OC_INVENTORY

        # Register resolvers
        register_resolvers(self.inventory_path)
        if self.inventory_path not in sys.path:
            sys.path.insert(0, self.inventory_path)
        from resolvers import pass_resolvers

        for name, func in pass_resolvers().items():
            if not OmegaConf.has_resolver(name):
                OmegaConf.register_new_resolver(name, func)

        sys.argv = ["kapitan", "compile"]
        args = build_parser().parse_args()
        args.inventory_backend = self.backend_id
        kapitan.cached.args = args

    def test_inventory_target(self):
        inv = inventory(
            inventory_path=self.inventory_path, target_name="nginx-dump-and-write"
        )
        logger.debug(inv)
        self.assertEqual(inv["parameters"]["target_name"], "nginx-dump-and-write")

    def test_inventory_all_targets(self):
        inv = inventory(inventory_path=self.inventory_path)
        self.assertNotEqual(inv.get("nginx-dump-and-write"), None)
        self.assertEqual(len(inv), 1)


del InventoryTargetTestBase  # remove InventoryTargetTestBase so that it doesn't run
