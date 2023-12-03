#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import sys
import unittest

import kapitan.cached
from kapitan.cli import build_parser
from kapitan.resources import inventory


class InventoryTargetTest(unittest.TestCase):
    
    def setUp(self) -> None:    
        sys.argv = ["kapitan", "compile" ] 
        args = build_parser().parse_args()
        kapitan.cached.args[args.name] = args
    
        
    def test_inventory_target(self):
        inv = inventory(["examples/kubernetes"], "minikube-es")
        self.assertEqual(inv["parameters"]["cluster"]["name"], "minikube")

    def test_inventory_all_targets(self):
        inv = inventory(["examples/kubernetes"], None)
        self.assertNotEqual(inv.get("minikube-es"), None)
