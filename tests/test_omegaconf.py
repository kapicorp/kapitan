#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests for omegaconf backend"

import logging
import os
import shutil
import tempfile
import unittest

from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.errors import InventoryError
from kapitan.inventory import get_inventory_backend
from kapitan.inventory.backends.omegaconf import OmegaConfInventory
from kapitan.inventory.backends.omegaconf.migrate import migrate_dir, migrate_str
from kapitan.inventory.backends.omegaconf.resolvers import (
    LITERAL_MARKER_PREFIX,
    LITERAL_MARKER_SUFFIX,
    process_literals,
    register_resolvers,
)
from kapitan.resources import get_inventory


logger = logging.getLogger(__name__)

TEST_PWD = os.getcwd()
TEST_KUBERNETES_INVENTORY = os.path.join(TEST_PWD, "examples/kubernetes/")


class InventoryTestOmegaConfKubernetes(unittest.TestCase):
    """Test OmegaConf inventory backend with examples/kubernetes inventory"""

    temp_dir = tempfile.mkdtemp()

    def setUp(self) -> None:
        shutil.copytree(TEST_KUBERNETES_INVENTORY, self.temp_dir, dirs_exist_ok=True)
        inventory_backend = get_inventory_backend("omegaconf")
        self.inventory_path = self.temp_dir
        self.extraArgv = ["--inventory-backend=omegaconf"]
        from kapitan.inventory.backends.omegaconf import migrate

        inventory_path = os.path.join(self.temp_dir, "inventory")
        migrate(inventory_path)
        register_resolvers(inventory_path)
        self.inventory_backend = inventory_backend(
            inventory_path=inventory_path, initialise=False
        )

    def test_load_and_resolve_single_target(self):
        target_name = "minikube"
        target_kapitan_metadata = dict(
            {
                "_kapitan_": {
                    "name": {
                        "short": "minikube",
                        "full": "minikube",
                        "path": "minikube-es",
                        "parts": ["minikube"],
                    }
                }
            }
        )

        # Load inventory but does not initialises targets
        inventory = self.inventory_backend

        # Manually create a new Target
        target = inventory.target_class(name=target_name, path="minikube-es.yml")
        logger.debug(f"Loading target {target_name} from {target.path}")
        logger.debug(target.parameters)
        # Adds target to Inventory
        inventory.targets.update({target_name: target})

        # Loads the target using the inventory
        inventory.load_target(target)

        # Check if the target is loaded correctly
        metadata = target.parameters.model_dump(by_alias=True)["_kapitan_"]
        self.assertDictEqual(target_kapitan_metadata["_kapitan_"], metadata)
        self.assertEqual(metadata["name"]["short"], "minikube")
        self.assertEqual(target.parameters.target_name, "minikube-es")
        self.assertEqual(target.parameters.kubectl["insecure_skip_tls_verify"], False)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
        return super().tearDown()


# Deferred resolver, merge resolver, and custom resolver tests are covered by
# the example-backed suite in tests/test_inventory_backend_examples.py.


class TestOmegaConfMigrate(unittest.TestCase):
    """Tests for the OmegaConf migration logic."""

    def test_migrate_str_converts_colon_to_dot(self):
        """Reclass ${foo:bar} becomes OmegaConf ${foo.bar}"""
        self.assertEqual(migrate_str("${a:b}"), "${a.b}")
        self.assertEqual(migrate_str("${a:b:c}"), "${a.b.c}")

    def test_migrate_dir_raises_on_invalid_yaml(self):
        """Migration errors must be raised, not swallowed."""
        temp_dir = tempfile.mkdtemp()
        bad_file = os.path.join(temp_dir, "bad.yml")
        with open(bad_file, "w") as f:
            f.write("parameters:\n  foo: bar\n")

        # Make the file read-only so migrate_file can't write
        os.chmod(bad_file, 0o444)

        try:
            with self.assertRaises(InventoryError):
                migrate_dir(temp_dir)
        finally:
            os.chmod(bad_file, 0o644)
            shutil.rmtree(temp_dir)


class TestOmegaConfClassResolution(unittest.TestCase):
    """Tests for OmegaConf class file resolution."""

    def test_resolve_class_file_path_with_yaml_extension(self):
        """Class files with .yaml extension must be discoverable."""
        temp_dir = tempfile.mkdtemp()
        classes_dir = os.path.join(temp_dir, "classes")
        targets_dir = os.path.join(temp_dir, "targets")
        os.makedirs(classes_dir)
        os.makedirs(targets_dir)

        # Create a .yaml class file
        with open(os.path.join(classes_dir, "common.yaml"), "w") as f:
            f.write("parameters:\n  foo: bar\n")

        # Create a target that references the class
        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write("classes:\n  - common\n")

        inventory = OmegaConfInventory(inventory_path=temp_dir, initialise=False)
        resolved = inventory.resolve_class_file_path("common")
        self.assertEqual(resolved, os.path.join(classes_dir, "common.yaml"))

        shutil.rmtree(temp_dir)

    def test_resolve_class_file_path_prefers_yml_over_yaml(self):
        """When both .yml and .yaml exist, .yml should take precedence."""
        temp_dir = tempfile.mkdtemp()
        classes_dir = os.path.join(temp_dir, "classes")
        targets_dir = os.path.join(temp_dir, "targets")
        os.makedirs(classes_dir)
        os.makedirs(targets_dir)

        with open(os.path.join(classes_dir, "common.yml"), "w") as f:
            f.write("parameters:\n  from: yml\n")
        with open(os.path.join(classes_dir, "common.yaml"), "w") as f:
            f.write("parameters:\n  from: yaml\n")

        inventory = OmegaConfInventory(inventory_path=temp_dir, initialise=False)
        resolved = inventory.resolve_class_file_path("common")
        self.assertEqual(resolved, os.path.join(classes_dir, "common.yml"))

        shutil.rmtree(temp_dir)


class TestOmegaConfProcessLiterals(unittest.TestCase):
    """Tests for escaped interpolation marker processing."""

    def test_process_literals_preserves_unmodified_tree(self):
        data = {"a": ["plain", {"nested": "value"}], "b": 1}

        result = process_literals(data)

        self.assertIs(result, data)
        self.assertIs(result["a"], data["a"])
        self.assertIs(result["a"][1], data["a"][1])

    def test_process_literals_copies_only_changed_branches(self):
        literal = f"prefix {LITERAL_MARKER_PREFIX}USER{LITERAL_MARKER_SUFFIX}"
        unchanged = {"nested": "value"}
        data = {"a": ["plain", literal], "b": unchanged}

        result = process_literals(data)

        self.assertIsNot(result, data)
        self.assertIsNot(result["a"], data["a"])
        self.assertIs(result["b"], unchanged)
        self.assertEqual(result["a"][1], "prefix ${USER}")


class TestOmegaConfInventoryMigrationTiming(unittest.TestCase):
    """Tests that --migrate runs before inventory initialisation."""

    def setUp(self):
        reset_cache()
        self.temp_dir = tempfile.mkdtemp()
        inventory_dir = os.path.join(self.temp_dir, "inventory")
        classes_dir = os.path.join(inventory_dir, "classes")
        targets_dir = os.path.join(inventory_dir, "targets")
        os.makedirs(classes_dir)
        os.makedirs(targets_dir)

        # Class with reclass-style interpolation
        with open(os.path.join(classes_dir, "common.yml"), "w") as f:
            f.write("parameters:\n  shared:\n    name: common\n")

        with open(os.path.join(classes_dir, "app.yml"), "w") as f:
            f.write(
                "classes:\n  - common\nparameters:\n  app:\n    ref: ${shared:name}\n"
            )

        with open(os.path.join(targets_dir, "test.yml"), "w") as f:
            f.write("classes:\n  - app\n")

        self.inventory_path = inventory_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        reset_cache()

    def test_migrate_runs_before_initialisation(self):
        """When cached.args.migrate is True, get_inventory must migrate files
        before the backend tries to render them."""
        from argparse import Namespace

        cached.args = Namespace(
            migrate=True,
            inventory_backend="omegaconf",
            compose_target_name=False,
            compose_node_name=False,
        )

        inventory = get_inventory(self.inventory_path)
        self.assertIsInstance(inventory, OmegaConfInventory)
        self.assertIn("test", inventory.targets)

        # Verify the file was actually migrated
        with open(os.path.join(self.inventory_path, "classes", "app.yml")) as f:
            content = f.read()
        self.assertIn("${shared.name}", content)
        self.assertNotIn("${shared:name}", content)
