#!/usr/bin/env python3

# Copyright 2023 neXenio

import tempfile
import unittest
import os
import yaml

from kapitan.inventory import OmegaConfBackend


class OmegaConfMigrationTest(unittest.TestCase):
    def test_migration_loading_directory(self):
        content = "content"
        expected = "content"

        dir = tempfile.mkdtemp()
        path = os.path.join(dir, "targets", "test.yml")
        os.makedirs(os.path.join(dir, "targets"))
        with open(path, "w+") as fp:
            yaml.dump(content, fp)

        OmegaConfBackend.migrate(dir)

        with open(path) as fp:
            migrated = yaml.load(fp, yaml.CSafeLoader)

        self.assertEqual(migrated, expected)

    def test_migration_loading_file(self):
        content = "content"
        expected = "content"

        file = tempfile.mktemp()
        with open(file, "w+") as fp:
            yaml.dump(content, fp)

        OmegaConfBackend.migrate(file)

        with open(file) as fp:
            migrated = yaml.load(fp, yaml.CSafeLoader)

        self.assertEqual(migrated, expected)

    def test_migration_loading_string(self):
        content = yaml.dump("content")
        expected = yaml.dump("content")

        migrated = OmegaConfBackend.migrate(content)
        self.assertEqual(migrated, expected)

    def test_migration_simple_interpolation(self):
        content = yaml.dump({"a": "${ref}"})
        expected = yaml.dump({"a": "${ref}"})

        migrated = OmegaConfBackend.migrate(content)
        self.assertEqual(migrated, expected)

    def test_migration_colon_interpolation(self):
        content = yaml.dump({"a": "${ref:ref}"})
        expected = yaml.dump({"a": "${ref.ref}"})

        migrated = OmegaConfBackend.migrate(content)
        self.assertEqual(migrated, expected)

    def test_migration_complex_interpolation(self):
        content = yaml.dump({"a": "${ref:${ref:ref}}"})
        expected = yaml.dump({"a": "${ref.${ref.ref}}"})

        migrated = OmegaConfBackend.migrate(content)
        self.assertEqual(migrated, expected)

    def test_migration_escaped_interpolation(self):
        content = yaml.dump({"a": "\\${ref}"})
        expected = yaml.dump({"a": "${tag:ref}"})

        migrated = OmegaConfBackend.migrate(content)
        self.assertEqual(migrated, expected)

    def test_migration_escaped_invalid_chars_interpolation(self):
        content = yaml.dump({"a": "\\${!ref}"})
        expected = yaml.dump({"a": "\\\\\\${!ref}"})

        migrated = OmegaConfBackend.migrate(content)
        self.assertEqual(migrated, expected)

    def test_migration_meta_interpolation(self):
        content = yaml.dump({"a": "${_reclass_:target_name}"})
        expected = yaml.dump({"a": "${_meta_.target_name}"})

        migrated = OmegaConfBackend.migrate(content)
        self.assertEqual(migrated, expected)
