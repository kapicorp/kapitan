#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for kapitan.targets — search_targets, load_target_inventory, compile_target."""

import unittest
from unittest.mock import MagicMock

from kapitan.errors import CompileError, InventoryError
from kapitan.targets import (
    compile_target,
    load_target_inventory,
    search_targets,
)


class MockTarget:
    def __init__(self, name, labels=None, has_params=True, has_kapitan=True):
        self.name = name
        self.parameters = MagicMock()
        if has_params:
            self.parameters.kapitan = MagicMock()
            self.parameters.kapitan.labels = labels or {}
            self.parameters.kapitan.compile = []
            self.parameters.kapitan.vars = MagicMock()
            self.parameters.kapitan.vars.target = name
            if not has_kapitan:
                self.parameters.kapitan = None
        else:
            self.parameters = None


class MockInventory:
    def __init__(self, targets):
        self.targets = targets

    def get_targets(self, requested_targets):
        return {
            name: target
            for name, target in self.targets.items()
            if name in requested_targets
        }


class SearchTargetsTest(unittest.TestCase):
    def test_no_labels_returns_original_targets(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1"),
                "t2": MockTarget("t2"),
            }
        )
        result = search_targets(inv, ["t1", "t2"], None)
        self.assertEqual(result, ["t1", "t2"])

    def test_labels_filter_matching_targets(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1", labels={"env": "prod", "app": "web"}),
                "t2": MockTarget("t2", labels={"env": "dev", "app": "web"}),
                "t3": MockTarget("t3", labels={"env": "prod", "app": "api"}),
            }
        )
        result = search_targets(inv, None, ["env=prod"])
        self.assertEqual(sorted(result), ["t1", "t3"])

    def test_multiple_labels_all_must_match(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1", labels={"env": "prod", "app": "web"}),
                "t2": MockTarget("t2", labels={"env": "prod", "app": "api"}),
                "t3": MockTarget("t3", labels={"env": "dev", "app": "web"}),
            }
        )
        result = search_targets(inv, None, ["env=prod", "app=web"])
        self.assertEqual(result, ["t1"])

    def test_no_matching_labels_raises_compile_error(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1", labels={"env": "prod"}),
            }
        )
        with self.assertRaises(CompileError) as ctx:
            search_targets(inv, None, ["env=dev"])
        self.assertIn("No targets found with labels", str(ctx.exception))

    def test_invalid_label_format_raises_compile_error(self):
        inv = MockInventory({"t1": MockTarget("t1")})
        with self.assertRaises(CompileError) as ctx:
            search_targets(inv, None, ["invalid_label"])
        self.assertIn("Failed to parse labels", str(ctx.exception))

    def test_label_key_missing_on_target_skips_target(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1", labels={"env": "prod"}),
                "t2": MockTarget("t2", labels={"app": "web"}),
            }
        )
        result = search_targets(inv, None, ["env=prod"])
        self.assertEqual(result, ["t1"])

    def test_empty_labels_list_returns_original(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1"),
            }
        )
        result = search_targets(inv, ["t1"], [])
        self.assertEqual(result, ["t1"])


class LoadTargetInventoryTest(unittest.TestCase):
    def test_load_all_targets(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1"),
                "t2": MockTarget("t2"),
            }
        )
        result = load_target_inventory(inv, None)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].target_full_path, "t1")
        self.assertEqual(result[1].target_full_path, "t2")

    def test_load_selected_targets(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1"),
                "t2": MockTarget("t2"),
            }
        )
        result = load_target_inventory(inv, ["t1"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_full_path, "t1")

    def test_empty_parameters_raises_inventory_error(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1", has_params=False),
            }
        )
        with self.assertRaises(InventoryError) as ctx:
            load_target_inventory(inv, None)
        self.assertIn("parameters is empty", str(ctx.exception))

    def test_empty_parameters_ignored_when_ignore_class_not_found(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1", has_params=False),
                "t2": MockTarget("t2"),
            }
        )
        result = load_target_inventory(inv, None, ignore_class_not_found=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_full_path, "t2")

    def test_empty_kapitan_raises_inventory_error(self):
        inv = MockInventory(
            {
                "t1": MockTarget("t1", has_kapitan=False),
            }
        )
        with self.assertRaises(InventoryError) as ctx:
            load_target_inventory(inv, None)
        self.assertIn("parameters.kapitan has no assignment", str(ctx.exception))

    def test_target_name_with_dots_replaced(self):
        inv = MockInventory(
            {
                "t1.name": MockTarget("t1.name"),
            }
        )
        result = load_target_inventory(inv, None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_full_path, "t1/name")

    def test_missing_inventory_target_key_skips_target(self):
        """When inventory.targets[target_name] raises KeyError, the target is skipped."""
        target = MockTarget("t1")
        inv = MockInventory({"t1": target})
        # Remove t1 from inv.targets so that inventory.targets[target_name]
        # raises KeyError inside load_target_inventory.
        del inv.targets["t1"]

        result = load_target_inventory(inv, None)
        self.assertEqual(len(result), 0)


class CompileTargetTest(unittest.TestCase):
    def test_compile_target_success(self):
        target_config = MagicMock()
        target_config.compile = []
        target_config.vars.target = "test-target"
        target_config.target_full_path = "test-target"

        args = MagicMock()
        args.inventory_pool_cache = False
        args.path_traversal_mode = "warn"

        # Should not raise
        compile_target(target_config, [], "/tmp", None, args)

    def test_compile_target_with_continue_on_error(self):
        target_config = MagicMock()
        compile_item = MagicMock()
        compile_item.input_type = "INVALID_TYPE"
        compile_item.continue_on_compile_error = True
        target_config.compile = [compile_item]
        target_config.vars.target = "test-target"
        target_config.target_full_path = "test-target"

        args = MagicMock()
        args.inventory_pool_cache = False
        args.path_traversal_mode = "warn"

        # Should not raise because continue_on_compile_error=True
        compile_target(target_config, [], "/tmp", None, args)

    def test_compile_target_without_continue_on_error(self):
        target_config = MagicMock()
        compile_item = MagicMock()
        compile_item.input_type = "INVALID_TYPE"
        compile_item.continue_on_compile_error = False
        target_config.compile = [compile_item]
        target_config.vars.target = "test-target"
        target_config.target_full_path = "test-target"

        args = MagicMock()
        args.inventory_pool_cache = False
        args.path_traversal_mode = "warn"

        with self.assertRaises(CompileError):
            compile_target(target_config, [], "/tmp", None, args)
