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

from kapitan.inventory import InventoryBackends, get_inventory_backend
from kapitan.inventory.inventory import InventoryError


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
