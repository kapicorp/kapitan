#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import unittest

from kapitan.resources import inventory


class InventoryTargetTest(unittest.TestCase):
    def test_inventory_target(self):
        inv = inventory(["examples/kubernetes"], "minikube-es")
        self.assertEqual(inv["parameters"]["cluster"]["name"], "minikube")

    def test_inventory_all_targets(self):
        inv = inventory(["examples/kubernetes"], None)
        self.assertNotEqual(inv.get("minikube-es"), None)
