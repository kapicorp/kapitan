#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"linter tests"

import logging
import os
import tempfile
import unittest

from kapitan.errors import KapitanError
from kapitan.lint import (
    lint_orphan_secrets,
    lint_unused_classes,
    lint_yamllint,
    start_lint,
)


logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
logger = logging.getLogger(__name__)


class Object:
    pass


class LinterTest(unittest.TestCase):
    def test_lint(self):
        args = Object()
        args.fail_on_warning = False
        args.skip_class_checks = False
        args.skip_yamllint = False
        args.inventory_path = "./tests/test_resources/inventory"
        args.search_secrets = True
        args.refs_path = "./tests/test_resources/secrets"
        args.compiled_path = "./tests/test_resources/compiled"

        num_issues_found = start_lint(args)
        desired_output = 3
        self.assertEqual(num_issues_found, desired_output)


class LintUnusedClassesTest(unittest.TestCase):
    """Unit tests for lint_unused_classes."""

    def test_no_unused_classes(self):
        with tempfile.TemporaryDirectory() as inventory:
            classes_dir = os.path.join(inventory, "classes")
            targets_dir = os.path.join(inventory, "targets")
            os.makedirs(classes_dir)
            os.makedirs(targets_dir)

            with open(os.path.join(classes_dir, "common.yml"), "w") as f:
                f.write("parameters:\n  key: value\n")

            with open(os.path.join(targets_dir, "test.yml"), "w") as f:
                f.write("classes:\n  - common\n")

            result = lint_unused_classes(inventory)
            self.assertEqual(result, 0)

    def test_finds_unused_classes(self):
        with tempfile.TemporaryDirectory() as inventory:
            classes_dir = os.path.join(inventory, "classes")
            targets_dir = os.path.join(inventory, "targets")
            os.makedirs(classes_dir)
            os.makedirs(targets_dir)

            with open(os.path.join(classes_dir, "common.yml"), "w") as f:
                f.write("parameters:\n  key: value\n")

            with open(os.path.join(classes_dir, "orphan.yml"), "w") as f:
                f.write("parameters:\n  key: value\n")

            with open(os.path.join(targets_dir, "test.yml"), "w") as f:
                f.write("classes:\n  - common\n")

            result = lint_unused_classes(inventory)
            self.assertEqual(result, 1)

    def test_init_class_handling(self):
        with tempfile.TemporaryDirectory() as inventory:
            classes_dir = os.path.join(inventory, "classes")
            targets_dir = os.path.join(inventory, "targets")
            os.makedirs(classes_dir)
            os.makedirs(targets_dir)

            # Create an init.yml class
            with open(os.path.join(classes_dir, "init.yml"), "w") as f:
                f.write("parameters:\n  key: value\n")

            # Reference it without .init suffix (reclass convention)
            with open(os.path.join(targets_dir, "test.yml"), "w") as f:
                f.write("classes:\n  - init\n")

            result = lint_unused_classes(inventory)
            self.assertEqual(result, 0)

    def test_missing_classes_dir_raises(self):
        with tempfile.TemporaryDirectory() as inventory:
            with self.assertRaises(KapitanError):
                lint_unused_classes(inventory)


class LintOrphanSecretsTest(unittest.TestCase):
    """Unit tests for lint_orphan_secrets."""

    def test_no_orphan_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            compiled_dir = os.path.join(tmp, "compiled")
            refs_dir = os.path.join(tmp, "refs")
            os.makedirs(compiled_dir)
            os.makedirs(refs_dir)

            with open(os.path.join(refs_dir, "secret1"), "w") as f:
                f.write("type: gpg\n")

            with open(os.path.join(compiled_dir, "output.yml"), "w") as f:
                f.write("value: ?{gpg:secret1}\n")

            result = lint_orphan_secrets(compiled_dir, refs_dir)
            self.assertEqual(result, 0)

    def test_finds_orphan_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            compiled_dir = os.path.join(tmp, "compiled")
            refs_dir = os.path.join(tmp, "refs")
            os.makedirs(compiled_dir)
            os.makedirs(refs_dir)

            with open(os.path.join(refs_dir, "used"), "w") as f:
                f.write("type: gpg\n")

            with open(os.path.join(refs_dir, "orphan"), "w") as f:
                f.write("type: gpg\n")

            with open(os.path.join(compiled_dir, "output.yml"), "w") as f:
                f.write("value: ?{gpg:used}\n")

            result = lint_orphan_secrets(compiled_dir, refs_dir)
            self.assertEqual(result, 1)

    def test_empty_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            compiled_dir = os.path.join(tmp, "compiled")
            refs_dir = os.path.join(tmp, "refs")
            os.makedirs(compiled_dir)
            os.makedirs(refs_dir)

            result = lint_orphan_secrets(compiled_dir, refs_dir)
            self.assertEqual(result, 0)


class LintYamllintTest(unittest.TestCase):
    """Unit tests for lint_yamllint."""

    def test_no_issues(self):
        with tempfile.TemporaryDirectory() as inventory:
            with open(os.path.join(inventory, "good.yml"), "w") as f:
                f.write("key: value\n")

            result = lint_yamllint(inventory)
            self.assertEqual(result, 0)

    def test_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as inventory:
            with open(os.path.join(inventory, "bad.yml"), "w") as f:
                f.write("key: value1\nkey: value2\n")

            result = lint_yamllint(inventory)
            self.assertGreater(result, 0)

    def test_octal_values(self):
        with tempfile.TemporaryDirectory() as inventory:
            with open(os.path.join(inventory, "octal.yml"), "w") as f:
                f.write("permissions: 0755\n")

            result = lint_yamllint(inventory)
            self.assertGreater(result, 0)
