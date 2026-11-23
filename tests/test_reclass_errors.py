#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"reclass error message tests"

import os
import shutil
import tempfile
import unittest
from unittest import mock

import pytest
from reclass.errors import NotFoundError

from kapitan.cli import main as kapitan
from kapitan.inventory import InventoryBackends, get_inventory_backend
from kapitan.inventory.inventory import InventoryError
from tests.test_helpers import create_test_inventory


class ReclassErrorMessageTest(unittest.TestCase):
    def setUp(self):
        self.inventory = get_inventory_backend(InventoryBackends.RECLASS)

    def test_class_not_found_includes_target_and_path(self):
        """ClassNotFound errors should include the target name and file path."""
        temp_dir = tempfile.mkdtemp()
        targets_dir = os.path.join(temp_dir, "targets")
        classes_dir = os.path.join(temp_dir, "classes")
        os.makedirs(targets_dir)
        os.makedirs(classes_dir)

        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write(
                "classes:\n  - missing.class\nparameters:\n  kapitan:\n    compile: []\n"
            )

        with self.assertRaises(InventoryError) as cm:
            self.inventory(inventory_path=temp_dir)

        error_msg = str(cm.exception)
        self.assertIn("test", error_msg)
        self.assertIn("missing.class", error_msg)
        self.assertIn("targets/test.yml", error_msg)
        self.assertIsNotNone(cm.exception.__cause__)

        shutil.rmtree(temp_dir)

    def test_type_merge_error_includes_path(self):
        """TypeMergeError should include the parameter path and file paths."""
        temp_dir = tempfile.mkdtemp()
        targets_dir = os.path.join(temp_dir, "targets")
        classes_dir = os.path.join(temp_dir, "classes")
        os.makedirs(targets_dir)
        os.makedirs(classes_dir)

        with open(os.path.join(classes_dir, "common.yml"), "w") as f:
            f.write("parameters:\n  foo: bar\n")
        with open(os.path.join(classes_dir, "other.yml"), "w") as f:
            f.write("parameters:\n  foo:\n    - list_item\n")
        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write(
                "classes:\n  - common\n  - other\nparameters:\n  kapitan:\n    compile: []\n"
            )

        with self.assertRaises(InventoryError) as cm:
            self.inventory(inventory_path=temp_dir)

        error_msg = str(cm.exception)
        self.assertIn("Cannot merge", error_msg)
        self.assertIn("foo", error_msg)
        self.assertIn("common.yml", error_msg)
        self.assertIn("other.yml", error_msg)
        self.assertIsNotNone(cm.exception.__cause__)

        shutil.rmtree(temp_dir)

    def test_inventory_error_has_cause(self):
        """InventoryError should preserve the original reclass exception as __cause__."""
        temp_dir = tempfile.mkdtemp()
        targets_dir = os.path.join(temp_dir, "targets")
        classes_dir = os.path.join(temp_dir, "classes")
        os.makedirs(targets_dir)
        os.makedirs(classes_dir)

        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write("classes:\n  - missing\nparameters:\n  kapitan:\n    compile: []\n")

        with self.assertRaises(InventoryError) as cm:
            self.inventory(inventory_path=temp_dir)

        self.assertIsNotNone(cm.exception.__cause__)
        self.assertTrue(hasattr(cm.exception.__cause__, "message"))

        shutil.rmtree(temp_dir)


class ReclassRsErrorMessageTest(ReclassErrorMessageTest):
    def setUp(self):
        self.inventory = get_inventory_backend(InventoryBackends.RECLASS_RS)

    def test_class_not_found_includes_target_and_path(self):
        """Reclass-rs errors should include the target name and missing class."""
        temp_dir = tempfile.mkdtemp()
        targets_dir = os.path.join(temp_dir, "targets")
        classes_dir = os.path.join(temp_dir, "classes")
        os.makedirs(targets_dir)
        os.makedirs(classes_dir)

        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write(
                "classes:\n  - missing.class\nparameters:\n  kapitan:\n    compile: []\n"
            )

        with self.assertRaises(InventoryError) as cm:
            self.inventory(inventory_path=temp_dir)

        error_msg = str(cm.exception)
        self.assertIn("test", error_msg)
        self.assertIn("missing.class", error_msg)
        self.assertIsNotNone(cm.exception.__cause__)

        shutil.rmtree(temp_dir)

    def test_type_merge_error_includes_path(self):
        """Reclass-rs type merge errors should mention the node and parameter."""
        temp_dir = tempfile.mkdtemp()
        targets_dir = os.path.join(temp_dir, "targets")
        classes_dir = os.path.join(temp_dir, "classes")
        os.makedirs(targets_dir)
        os.makedirs(classes_dir)

        with open(os.path.join(classes_dir, "common.yml"), "w") as f:
            f.write("parameters:\n  foo: bar\n")
        with open(os.path.join(classes_dir, "other.yml"), "w") as f:
            f.write("parameters:\n  foo:\n    - list_item\n")
        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write(
                "classes:\n  - common\n  - other\nparameters:\n  kapitan:\n    compile: []\n"
            )

        with self.assertRaises(InventoryError) as cm:
            self.inventory(inventory_path=temp_dir)

        error_msg = str(cm.exception)
        self.assertIn("test", error_msg)
        self.assertIn("foo", error_msg)
        self.assertIsNotNone(cm.exception.__cause__)

        shutil.rmtree(temp_dir)

    def test_inventory_error_has_cause(self):
        """InventoryError should preserve the original reclass-rs exception as __cause__."""
        temp_dir = tempfile.mkdtemp()
        targets_dir = os.path.join(temp_dir, "targets")
        classes_dir = os.path.join(temp_dir, "classes")
        os.makedirs(targets_dir)
        os.makedirs(classes_dir)

        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write("classes:\n  - missing\nparameters:\n  kapitan:\n    compile: []\n")

        with self.assertRaises(InventoryError) as cm:
            self.inventory(inventory_path=temp_dir)

        self.assertIsNotNone(cm.exception.__cause__)
        self.assertIsInstance(cm.exception.__cause__, ValueError)

        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()


@pytest.mark.usefixtures("isolated_compile_dir")
class CompileErrorLoggingTest(unittest.TestCase):
    """kapitan compile logs the actual error instead of exiting silently or generically."""

    def _assert_compile_logs(self, expected, *args):
        with self.assertLogs("kapitan.targets", level="ERROR") as logs:
            with self.assertRaises(SystemExit):
                kapitan("compile", *args)
        self.assertIn(expected, "\n".join(logs.output))

    def test_unmatched_labels_are_logged(self):
        create_test_inventory(os.getcwd(), {"real": {"parameters": {"foo": 1}}})
        self._assert_compile_logs("No targets found with labels", "-l", "env=nope")

    def test_reclass_not_found_keeps_reclass_message(self):
        # the missing directory is named instead of a generic "inventory not found"
        with self.assertLogs("kapitan", level="ERROR") as logs:
            with self.assertRaises(SystemExit):
                kapitan("compile", "--inventory-path", "does-not-exist")
        self.assertIn(
            "No such directory: does-not-exist/targets", "\n".join(logs.output)
        )

    def test_reclass_not_found_during_compile_keeps_reclass_message(self):
        compile_entry = {"output_path": ".", "input_type": "copy", "input_paths": []}
        create_test_inventory(
            os.getcwd(),
            {"real": {"parameters": {"kapitan": {"compile": [compile_entry]}}}},
        )
        error = NotFoundError("No such directory: some/dependency")
        with mock.patch("kapitan.targets.fetch_dependencies", side_effect=error):
            self._assert_compile_logs("No such directory: some/dependency", "--fetch")
