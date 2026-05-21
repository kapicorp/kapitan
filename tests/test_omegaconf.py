#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests for omegaconf backend"

import importlib.util
import logging
import os
import shutil
import tempfile
import unittest

from omegaconf import OmegaConf

from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.errors import InventoryError
from kapitan.inventory import get_inventory_backend
from kapitan.inventory.backends.omegaconf import OmegaConfInventory
from kapitan.inventory.backends.omegaconf.migrate import migrate_dir, migrate_str
from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers
from kapitan.resources import get_inventory


logger = logging.getLogger(__name__)

TEST_PWD = os.getcwd()
TEST_KUBERNETES_INVENTORY = os.path.join(TEST_PWD, "examples/kubernetes/")
TEST_OMEGACONF_INVENTORY = os.path.join(
    TEST_PWD, "tests/test_resources/omegaconf/inventory"
)


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


class InventoryTestOmegaConfOC(unittest.TestCase):
    """Test OmegaConf inventory backend with test_resources/omegaconf inventory (deferred resolvers)"""

    @staticmethod
    def register_custom_resolvers():
        """Register custom resolvers from the test resources"""
        # Load resolvers module without modifying sys.path (parallel-test safe)
        spec = importlib.util.spec_from_file_location(
            "resolvers", os.path.join(TEST_OMEGACONF_INVENTORY, "resolvers.py")
        )
        resolvers_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolvers_module)

        custom_resolvers = resolvers_module.pass_resolvers()
        for name, func in custom_resolvers.items():
            if not OmegaConf.has_resolver(name):
                OmegaConf.register_new_resolver(name, func)

    def setUp(self) -> None:
        register_resolvers(TEST_OMEGACONF_INVENTORY)
        self.register_custom_resolvers()
        inventory_backend = get_inventory_backend("omegaconf")
        self.inventory_path = TEST_OMEGACONF_INVENTORY
        self.extraArgv = ["--inventory-backend=omegaconf"]
        self.inventory_backend = inventory_backend(
            inventory_path=TEST_OMEGACONF_INVENTORY, initialise=False
        )

    def test_load_and_resolve_single_target(self):
        target_name = "test-resolvers"
        target_path = "test-resolvers.yml"
        target_kapitan_metadata = dict(
            {
                "_kapitan_": {
                    "name": {
                        "short": "test-resolvers",
                        "full": "test-resolvers",
                        "path": "test-resolvers",
                        "parts": ["test-resolvers"],
                    }
                }
            }
        )

        # Load inventory but does not initialises targets
        inventory = self.inventory_backend

        # Manually create a new Target
        target = inventory.target_class(name=target_name, path=target_path)
        logger.debug(f"Loading target {target_name} from {target.path}")
        logger.debug(target.parameters)
        # Adds target to Inventory
        inventory.targets.update({target_name: target})

        # Loads the target using the inventory
        inventory.load_target(target)

        # Check if the target is loaded correctly
        metadata = target.parameters.model_dump(by_alias=True)["_kapitan_"]
        self.assertDictEqual(target_kapitan_metadata["_kapitan_"], metadata)
        self.assertEqual(metadata["name"]["short"], "test-resolvers")
        self.assertEqual(target.parameters.target_name, "test-resolvers")

    def test_load_class_with_empty_values(self):
        """Test that classes with null/empty 'classes:' and 'parameters:' values are handled correctly"""
        target_name = "test-merge"
        target_path = "test-merge.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})

        # This should not raise "'NoneType' object is not iterable" error
        # because the _empty_classes.yml has a "classes:" with no value (null)
        inventory.load_target(target)

        # Verify that parameters from _empty_classes.yml were loaded
        params = target.parameters.model_dump(by_alias=True)
        self.assertTrue(
            params.get("merge_tests", {}).get("extra_option_from_empty_class", False),
            "Parameter from _empty_classes.yml should be loaded",
        )

    def test_custom_resolvers_get_suffix_and_substr(self):
        """Test custom resolvers: get_suffix and get_substr"""
        target_name = "test-resolvers"
        target_path = "test-resolvers.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        # get_suffix should extract "resolvers" from "test-resolvers"
        self.assertEqual(
            params["resolver_test"]["target_suffix"],
            "resolvers",
            "get_suffix resolver should extract last part of hyphenated string",
        )
        # get_substr should extract "test" (index -2 from ["test", "resolvers"])
        self.assertEqual(
            params["resolver_test"]["target_substr"],
            "test",
            "get_substr resolver should extract specified index from hyphenated string",
        )

    def test_conditional_if_resolver(self):
        """Test ${if:} conditional resolver"""
        target_name = "test-resolvers"
        target_path = "test-resolvers.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        # When condition is true, value should be present
        self.assertEqual(
            params["conditional_test"]["enabled_feature"],
            "enabled_value",
            "${if:} should return value when condition is true",
        )
        # When condition is false, value should be empty dict (omegaconf behavior)
        self.assertEqual(
            params["conditional_test"]["disabled_feature"],
            {},
            "${if:} should return empty dict when condition is false",
        )

    def test_ifelse_resolver(self):
        """Test ${ifelse:} conditional resolver with ${equal:}"""
        target_name = "test-resolvers"
        target_path = "test-resolvers.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        # environment is "dev", so ifelse should return "development_mode"
        self.assertEqual(
            params["conditional_test"]["env_check"],
            "development_mode",
            "${ifelse:} should return first value when condition matches",
        )

    def test_relpath_resolver_nested(self):
        """Test ${relpath:} resolver with nested structures"""
        target_name = "test-resolvers"
        target_path = "test-resolvers.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        # Check connection string uses relpath to access nested values
        expected_host = "db.resolvers-test.local"
        expected_port = 5432
        expected_connection = f"postgresql://{expected_host}:{expected_port}/mydb"

        self.assertEqual(params["nested_config"]["database"]["host"], expected_host)
        self.assertEqual(params["nested_config"]["database"]["port"], expected_port)
        self.assertEqual(
            params["nested_config"]["connection_string"],
            expected_connection,
            "${relpath:} should correctly resolve nested values",
        )

    def test_omegaconf_remove_config_present(self):
        """Test that omegaconf.remove configuration is present and correctly specified"""
        target_name = "test-resolvers"
        target_path = "test-resolvers.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        # omegaconf.remove should list the keys to remove during compile output
        self.assertIn("omegaconf", params)
        self.assertIn("remove", params["omegaconf"])
        self.assertIn(
            "base_component",
            params["omegaconf"]["remove"],
            "omegaconf.remove should contain base_component for removal during compile",
        )

    def test_escape_resolver_produces_dollar_syntax(self):
        """Test that ${escape:content} produces ${content} as a literal string."""
        target_name = "test-resolvers"
        target_path = "test-resolvers.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        escape_test = params["escape_test"]

        # Standalone values become ${content}
        self.assertEqual(
            escape_test["terraform_ref"],
            "${google_service_account.cluster.email}",
            "${escape:} should produce ${content} without omegaconf resolving it",
        )
        self.assertEqual(
            escape_test["shell_var"],
            "${HOME}",
            "${escape:} should preserve shell variable syntax literally",
        )

        # Embedded mid-string: surrounding text and other interpolations are unaffected
        self.assertEqual(
            escape_test["greeting"],
            "Hello ${USER}, welcome to resolvers-test",
            "${escape:} embedded in a string should only escape its own content",
        )

        # Content that matches a real inventory key must NOT be resolved
        self.assertNotEqual(
            escape_test["escaped_key"],
            escape_test["real_key"],
            "${escape:environment} must not resolve the 'environment' key",
        )
        self.assertEqual(
            escape_test["escaped_key"],
            "${environment}",
            "${escape:environment} should produce the literal string '${environment}'",
        )


class InventoryTestOmegaConfMergeResolver(unittest.TestCase):
    """Test OmegaConf merge resolver functionality"""

    @staticmethod
    def register_custom_resolvers():
        """Register custom resolvers from the test resources"""
        # Load resolvers module without modifying sys.path (parallel-test safe)
        spec = importlib.util.spec_from_file_location(
            "resolvers", os.path.join(TEST_OMEGACONF_INVENTORY, "resolvers.py")
        )
        resolvers_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolvers_module)

        custom_resolvers = resolvers_module.pass_resolvers()
        for name, func in custom_resolvers.items():
            if not OmegaConf.has_resolver(name):
                OmegaConf.register_new_resolver(name, func)

    def setUp(self) -> None:
        register_resolvers(TEST_OMEGACONF_INVENTORY)
        self.register_custom_resolvers()
        inventory_backend = get_inventory_backend("omegaconf")
        self.inventory_path = TEST_OMEGACONF_INVENTORY
        self.inventory_backend = inventory_backend(
            inventory_path=TEST_OMEGACONF_INVENTORY, initialise=False
        )

    def test_simple_two_way_merge(self):
        """Test simple two-way merge with override"""
        target_name = "test-merge"
        target_path = "test-merge.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        merged = params["merged_service"]

        # From defaults
        self.assertEqual(merged["type"], "ClusterIP")
        self.assertEqual(merged["protocol"], "TCP")
        self.assertEqual(merged["labels"]["managed-by"], "kapitan")

        # Overridden
        self.assertEqual(merged["port"], 8080)

        # Added
        self.assertEqual(merged["target_port"], 8080)

    def test_three_way_merge(self):
        """Test three-way merge combining multiple configs"""
        target_name = "test-merge"
        target_path = "test-merge.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        merged = params["merged_deployment"]

        # Overridden from deployment_custom
        self.assertEqual(merged["replicas"], 3)

        # From defaults
        self.assertEqual(merged["strategy"]["type"], "RollingUpdate")
        self.assertEqual(merged["strategy"]["rollingUpdate"]["maxSurge"], 1)

        # Merged annotations (from defaults + deployment_annotations)
        self.assertEqual(merged["pod_annotations"]["prometheus.io/scrape"], "true")
        self.assertEqual(
            merged["pod_annotations"]["custom.io/annotation"], "test-value"
        )

    def test_deep_nested_merge(self):
        """Test deep merge with nested objects"""
        target_name = "test-merge"
        target_path = "test-merge.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        merged = params["merged_nested"]

        # Preserved from base
        self.assertEqual(merged["level1"]["level2"]["value_a"], "base_a")
        self.assertEqual(merged["level1"]["other"], "base_other")

        # Overridden
        self.assertEqual(merged["level1"]["level2"]["value_b"], "override_b")

        # Added
        self.assertEqual(merged["level1"]["level2"]["value_c"], "new_c")

    def test_merge_list_concatenation(self):
        """Test that lists are concatenated during merge (omegaconf default behavior)"""
        target_name = "test-merge"
        target_path = "test-merge.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        merged = params["merged_lists"]

        # Lists are concatenated in omegaconf merge (base items + override items)
        self.assertEqual(
            merged["items"],
            ["item1", "item2", "item3", "item4", "item5"],
            "Lists should be concatenated during merge",
        )

        # Other values preserved
        self.assertEqual(merged["config"]["key"], "value")

    def test_merge_omegaconf_remove_config(self):
        """Test that omegaconf.remove is properly configured for compile-time removal"""
        target_name = "test-merge"
        target_path = "test-merge.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        # omegaconf.remove should list base objects to be removed during compile
        self.assertIn("omegaconf", params)
        remove_list = params["omegaconf"]["remove"]
        self.assertIn("service_defaults", remove_list)
        self.assertIn("deployment_defaults", remove_list)
        self.assertIn("monitoring_defaults", remove_list)


class InventoryTestOmegaConfDeferredResolvers(unittest.TestCase):
    """Test OmegaConf deferred resolver functionality (parentkey, _root_ context)"""

    @staticmethod
    def register_custom_resolvers():
        """Register custom resolvers from the test resources"""
        # Load resolvers module without modifying sys.path (parallel-test safe)
        spec = importlib.util.spec_from_file_location(
            "resolvers", os.path.join(TEST_OMEGACONF_INVENTORY, "resolvers.py")
        )
        resolvers_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolvers_module)

        custom_resolvers = resolvers_module.pass_resolvers()
        for name, func in custom_resolvers.items():
            if not OmegaConf.has_resolver(name):
                OmegaConf.register_new_resolver(name, func)

    def setUp(self) -> None:
        register_resolvers(TEST_OMEGACONF_INVENTORY)
        self.register_custom_resolvers()
        inventory_backend = get_inventory_backend("omegaconf")
        self.inventory_path = TEST_OMEGACONF_INVENTORY
        self.inventory_backend = inventory_backend(
            inventory_path=TEST_OMEGACONF_INVENTORY, initialise=False
        )

    def test_deferred_parentkey_resolves_at_definition(self):
        """Test \\${parentkey:} resolves to parent key at definition location.

        Note: parentkey resolves to the key name where the resolver is defined,
        not the key name after merge. This is the expected omegaconf behavior.
        """
        target_name = "test-deferred"
        target_path = "test-deferred.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        deployments = params["deployments"]

        # parentkey resolves to the original definition location, not merge destination
        # This documents the actual behavior of omegaconf's parentkey resolver
        self.assertEqual(
            deployments["web-app"]["name"],
            "deployment_template",
            "\\${parentkey:} resolves at definition time, not merge destination",
        )
        # All merged components share the same resolved parentkey from the template
        self.assertEqual(
            deployments["api-service"]["name"],
            "deployment_template",
        )
        self.assertEqual(
            deployments["worker-job"]["name"],
            "deployment_template",
        )

    def test_deferred_parentkey_in_nested_structure(self):
        """Test \\${parentkey:} in nested structures resolves to immediate parent key"""
        target_name = "test-deferred"
        target_path = "test-deferred.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        deployments = params["deployments"]

        # In labels, parentkey resolves to "labels" (the immediate parent key)
        self.assertEqual(
            deployments["web-app"]["labels"]["app.kubernetes.io/name"],
            "labels",
            "\\${parentkey:} in nested structure resolves to immediate parent key",
        )

    def test_custom_resolver_with_root_context(self):
        """Test custom resolver using _root_ to access target_name"""
        target_name = "test-deferred"
        target_path = "test-deferred.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)
        secrets = params["secrets"]

        # vaultkv resolver should use _root_.target_name in the path
        self.assertIn("test-deferred", secrets["db_password"])
        self.assertIn("database", secrets["db_password"])
        self.assertIn("?{vaultkv:", secrets["db_password"])

        self.assertIn("test-deferred", secrets["api_key"])
        self.assertIn("api", secrets["api_key"])

    def test_upper_custom_resolver(self):
        """Test ${upper:} custom resolver converts to uppercase"""
        target_name = "test-deferred"
        target_path = "test-deferred.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        self.assertEqual(
            params["uppercase_test"]["env_upper"],
            "PROD",
            "${upper:} should convert 'prod' to 'PROD'",
        )
        self.assertEqual(
            params["uppercase_test"]["cluster_upper"],
            "DEFERRED-TEST",
            "${upper:} should convert 'deferred-test' to 'DEFERRED-TEST'",
        )

    def test_capitalize_custom_resolver(self):
        """Test ${capitalize:} custom resolver for camelCase conversion"""
        target_name = "test-deferred"
        target_path = "test-deferred.yml"

        inventory = self.inventory_backend
        target = inventory.target_class(name=target_name, path=target_path)
        inventory.targets.update({target_name: target})
        inventory.load_target(target)

        params = target.parameters.model_dump(by_alias=True)

        # capitalize converts "test-deferred" to "testDeferred"
        self.assertEqual(
            params["capitalize_test"]["camel_name"],
            "testDeferred",
            "${capitalize:} should convert hyphenated name to camelCase",
        )


# Compile tests for omegaconf are in test_compile.py (CompileTestResourcesOCOmegaconf)


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
