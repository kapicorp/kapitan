#!/usr/bin/env python3

# Copyright 2023 neXenio

import os
import tempfile
import unittest

import yaml

from kapitan.inventory.omegaconf import OmegaConfBackend


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
        expected = yaml.dump({"a": "${escape:ref}"})

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


@unittest.skip("Pool issues")
class OmegaConfInventoryTest(unittest.TestCase):
    params: dict
    logfile: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory_path = tempfile.mkdtemp()

        target = """
        classes:
            # test absolute class
            - test.class
        
        parameters:
            target_name: target
            kapitan:
                vars:
                    target: target
            
            # test value
            value: test
            
            # test absolute interpolation
            absolute_interpolation: ${value}
            
            # test relative interpolation
            relative:
                value: test
                interpolation: ${.value}
            
            # test custom resolvers
            tag: ${escape:TAG}
            merge: ${merge:${merge1},${merge2}}
            merge1: 
                - value1
            merge2:
                - value2
            key: ${key:}
            full:
                key: ${fullkey:}
            
            # test overwrite prefix    
            overwrite: false
            
            # test redundant keys
            redundant: redundant
        """

        testclass = """
        classes:
            # test absolute class
            - .relative
            
        parameters:
            # indicator for success
            absolute_class: success
            
            # test redundant keys
            redundant: redundant
            
            # test overwrite prefix
            ~overwrite: true
        """

        relativeclass = """
        parameters:
            # indicator for success
            relative_class: success
        """

        targets_path = os.path.join(cls.inventory_path, "targets")
        os.makedirs(targets_path, exist_ok=True)
        with open(os.path.join(targets_path, "target.yml"), "w") as f:
            f.write(target)

        classes_path = os.path.join(cls.inventory_path, "classes", "test")
        os.makedirs(classes_path, exist_ok=True)
        with open(os.path.join(classes_path, "class.yml"), "w") as f:
            f.write(testclass)
        with open(os.path.join(classes_path, "relative.yml"), "w") as f:
            f.write(relativeclass)

        _, cls.logfile = tempfile.mkstemp(suffix=".log")

        # get inventory
        backend = OmegaConfBackend(cls.inventory_path, False, [], cls.logfile)
        inventory = backend.inventory()
        cls.params = inventory["nodes"]["target"]["parameters"]

    def test_absolute_class(self):
        self.assertTrue(self.params["absolute_class"])

    def test_relative_class(self):
        self.assertTrue(self.params["relative_class"])

    def test_value(self):
        self.assertEqual(self.params["value"], "test")

    def test_absolute_interpolation(self):
        self.assertEqual(self.params["absolute_interpolation"], "test")

    def test_relative_interpolation(self):
        self.assertEqual(self.params["relative"]["interpolation"], "test")

    def test_absolute_class(self):
        self.assertEqual(self.params["value"], "test")

    def test_absolute_class(self):
        self.assertEqual(self.params["tag"], "${TAG}")
        self.assertEqual(self.params["merge"], ["value1", "value2"])
        self.assertEqual(self.params["key"], "key")
        self.assertEqual(self.params["full"]["key"], "full.key")

    def test_overwrite_prefix(self):
        self.assertTrue(self.params["overwrite"])

    def test_meta_data(self):
        meta = self.params["_meta_"]
        self.assertTrue(meta)

    @unittest.skip
    def test_redundant_key_check(self):
        content = ""
        print(self.logfile)
        with open(self.logfile, "r") as f:
            print(f.read())

        expected = "value 'redundant' is defined redundantly in 'redundant'"
        self.assertEqual(content, expected)
