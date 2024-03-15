#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import argparse
import importlib
import unittest

from kapitan import cached
from kapitan.resources import inventory


class InventoryTargetTest(unittest.TestCase):
    def setUp(self):
        # Setup `cached.args` if it's not setup yet
        cached.args.setdefault("compile", argparse.Namespace())
        # Configure `compile.inventory_path` and `inventory-backend`. This
        # allows us to reuse the tests by inheriting from this test class.
        cached.args["compile"].inventory_path = "inventory"
        cached.args["inventory-backend"] = "reclass"

    def test_inventory_target(self):
        inv = inventory(["examples/kubernetes"], "minikube-es")
        self.assertEqual(inv["parameters"]["cluster"]["name"], "minikube")

    def test_inventory_all_targets(self):
        inv = inventory(["examples/kubernetes"], None)
        self.assertNotEqual(inv.get("minikube-es"), None)


class InventoryTargetTestReclassRs(InventoryTargetTest):
    def setUp(self):
        if not importlib.util.find_spec("reclass_rs"):
            self.skipTest("reclass-rs not available")

        super().setUp()
        cached.args["inventory-backend"] = "reclass-rs"
