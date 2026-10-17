#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""get_inventory explicit-parameter tests.

Proves get_inventory honors backend_id / compose_target_name / migrate /
enable_class_wildcards passed explicitly, without reading them from
kapitan.cached.args. cached.args is left deliberately empty so any reliance on
the global would surface.
"""

import importlib
import os
import shutil
import tempfile
import unittest
from argparse import Namespace

import kapitan.cached
from kapitan.inventory import InventoryBackends
from kapitan.resources import get_inventory


TEST_PWD = os.getcwd()
TEST_KUBERNETES_INVENTORY = os.path.join(TEST_PWD, "examples/kubernetes/inventory")


class GetInventoryExplicitParamsTest(unittest.TestCase):
    backend_id = InventoryBackends.RECLASS

    def setUp(self):
        if not importlib.util.find_spec(self.backend_id.replace("-", "_")):
            self.skipTest(f"backend module {self.backend_id} not available")
        # collision inventory: env1 duplicates every target -> only compose
        # resolves the name clash
        self.tmp = tempfile.mkdtemp()
        inv = os.path.join(self.tmp, "inventory")
        shutil.copytree(TEST_KUBERNETES_INVENTORY, inv)
        targets = os.path.join(inv, "targets")
        shutil.copytree(targets, os.path.join(targets, "env1"))
        self.inventory_path = inv
        # deliberately empty args: explicit params must drive behavior
        kapitan.cached.reset_cache()
        kapitan.cached.args = Namespace()

    def tearDown(self):
        kapitan.cached.reset_cache()
        shutil.rmtree(self.tmp)

    def test_compose_true_via_explicit_param(self):
        inv = get_inventory(
            self.inventory_path,
            backend_id=self.backend_id,
            compose_target_name=True,
        )
        names = inv.targets.keys()
        self.assertIn("minikube-es", names)
        self.assertIn("env1.minikube-es", names)

    def test_compose_false_via_explicit_param_collides(self):
        with self.assertRaises(SystemExit):
            get_inventory(
                self.inventory_path,
                backend_id=self.backend_id,
                compose_target_name=False,
            )


class GetInventoryExplicitParamsTestReclassRs(GetInventoryExplicitParamsTest):
    backend_id = InventoryBackends.RECLASS_RS
