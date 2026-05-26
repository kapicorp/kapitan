#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Backend example inventory tests.

These tests exercise the minimal example inventories under ``examples/reclass/``
and ``examples/omegaconf/`` to verify backend-specific features and catch
regressions in inventory handling.

.. note::
   Reclass and reclass-rs share the same example inventory because they are
   drop-in compatible at the file-format level. The only known runtime
   difference is that reclass-rs currently returns empty exports for some
   inventories (documented below).

   They have **separate golden snapshot directories** for compile output so that
   future divergences are caught immediately rather than masked by a shared
   snapshot.

Backend parity matrix
---------------------

Feature                           | reclass | reclass-rs | omegaconf
----------------------------------|---------|------------|----------
Class inheritance                 | yes     | yes        | yes
Nested classes (init.yml)         | yes     | yes        | yes
Parameter interpolation           | yes     | yes        | yes
Cross-file interpolation          | yes     | yes        | yes
List merge behaviour              | concat  | concat     | concat
Dict merge behaviour              | deep    | deep       | deep (via ``${merge:}``)
Scalar override                   | yes     | yes        | yes
Exports                           | yes     | no*        | yes
Escaped interpolation             | yes     | yes        | yes
Deferred interpolation            | n/a     | n/a        | yes
Custom resolvers                  | n/a     | n/a        | yes
Conditional resolvers             | n/a     | n/a        | yes
Arithmetic resolvers              | n/a     | n/a        | yes
Compile output structure          | yes     | yes        | yes

* Known difference: reclass-rs returns empty exports for some inventories.
"""

import importlib
import os

import pytest

import kapitan.cached
from kapitan.cached import reset_cache
from kapitan.cli import build_parser
from kapitan.inventory import InventoryBackends
from kapitan.resources import inventory as get_inventory
from tests.backend_examples import (
    OMEGACONF_EXAMPLE,
    OMEGACONF_INVENTORY,
    RECLASS_EXAMPLE,
    RECLASS_INVENTORY,
    TEST_PWD,
)
from tests.test_helpers import IsolatedTestEnvironment, run_kapitan_command


def _skip_if_backend_missing(backend_id):
    module = backend_id.replace("-", "_")
    if not importlib.util.find_spec(module):
        pytest.skip(f"backend module {module} not available")


def _set_backend_args(backend_id):
    args = build_parser().parse_args(["compile"])
    args.inventory_backend = backend_id
    kapitan.cached.args = args
    reset_cache()


@pytest.fixture(params=[InventoryBackends.RECLASS, InventoryBackends.RECLASS_RS])
def reclass_compatible_backend(request):
    """Parametrized fixture that yields reclass and reclass-rs backend IDs."""
    backend_id = request.param
    _skip_if_backend_missing(backend_id)
    _set_backend_args(backend_id)
    try:
        yield backend_id
    finally:
        reset_cache()
        kapitan.cached.args = build_parser().parse_args(["compile"])


@pytest.fixture
def omegaconf_backend():
    """Fixture that sets up the omegaconf backend with resolvers registered.

    Cleans up ``sys.path`` and ``sys.modules`` entries added by
    ``register_resolvers`` so the omegaconf example's ``resolvers.py`` does
    not leak into subsequent tests that share the same Python process.
    """
    import multiprocessing
    import sys

    _skip_if_backend_missing(InventoryBackends.OMEGACONF)
    from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers

    sys_path_before = list(sys.path)
    resolvers_module_before = sys.modules.get("resolvers")

    register_resolvers(OMEGACONF_INVENTORY)
    _set_backend_args(InventoryBackends.OMEGACONF)
    try:
        yield InventoryBackends.OMEGACONF
    finally:
        # Restore sys.path: register_resolvers appends the inventory dir so
        # ``from resolvers import pass_resolvers`` works. Without cleanup,
        # the cached ``resolvers`` module pollutes later tests.
        sys.path[:] = sys_path_before
        if resolvers_module_before is None:
            sys.modules.pop("resolvers", None)
        else:
            sys.modules["resolvers"] = resolvers_module_before
        # Clear OmegaConf's global resolver registry to avoid leaking
        # ``${merge:}``, ``${escape:}`` and user resolvers into later tests.
        from omegaconf import OmegaConf

        OmegaConf.clear_resolvers()
        reset_cache()
        kapitan.cached.args = build_parser().parse_args(["compile"])
        # Loading the omegaconf inventory triggers multiprocessing initialisation
        # which locks the start method to the platform default (``fork`` on Linux).
        # Later tests that compile with the reclass backend rely on ``spawn`` to
        # get a clean worker; without forcing it back here the kubernetes example
        # compile produces empty ``target_full_path`` values in worker output.
        try:
            multiprocessing.set_start_method("spawn", force=True)
        except RuntimeError:
            pass


# ---------------------------------------------------------------------------
# Shared assertions for reclass-compatible backends
# ---------------------------------------------------------------------------
class TestReclassExampleInventory:
    """Tests for the shared reclass example inventory.

    These tests run against both the Python ``reclass`` and Rust ``reclass-rs``
    backends to verify parity.
    """

    def test_inventory_targets_discovered(self, reclass_compatible_backend):
        inv = get_inventory(inventory_path=RECLASS_INVENTORY)
        assert "simple" in inv
        assert "advanced" in inv
        assert "compile-test" in inv

    def test_inventory_interpolation(self, reclass_compatible_backend):
        inv = get_inventory(
            inventory_path=RECLASS_INVENTORY, target_name="compile-test"
        )
        params = inv["parameters"]
        assert params["interpolated"] == "reclass-test"
        assert params["nested_interpolated"] == "https://reclass-test.example.com"
        assert params["ref_value"] == "info"

    def test_inventory_escaped_interpolation(self, reclass_compatible_backend):
        inv = get_inventory(
            inventory_path=RECLASS_INVENTORY, target_name="compile-test"
        )
        assert inv["parameters"]["escaped_value"] == "${app_name}"

    def test_inventory_list_merge(self, reclass_compatible_backend):
        inv = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="simple")
        # Reclass concatenates lists when included from multiple classes.
        assert inv["parameters"]["tags"] == ["base-tag", "common", "app-tag"]

    def test_inventory_dict_merge(self, reclass_compatible_backend):
        inv = get_inventory(
            inventory_path=RECLASS_INVENTORY, target_name="compile-test"
        )
        config = inv["parameters"]["config"]
        assert config["log_level"] == "info"
        assert config["retries"] == 3
        assert config["nested"]["key_a"] == "value_a"

    def test_inventory_nested_classes(self, reclass_compatible_backend):
        inv = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["init_value"] == "from_init"
        assert params["child_value"] == "from_child"
        assert params["child_override"] == "overridden"
        assert params["sibling_value"] == "from_sibling"

    def test_inventory_target_name(self, reclass_compatible_backend):
        inv = get_inventory(
            inventory_path=RECLASS_INVENTORY, target_name="compile-test"
        )
        assert inv["parameters"]["target_name"] == "compile-test"

    def test_inventory_scalar_override(self, reclass_compatible_backend):
        inv = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="advanced")
        # The advanced target overrides environment from "dev" to "staging".
        assert inv["parameters"]["environment"] == "staging"

    def test_inventory_missing_key_returns_none(self, reclass_compatible_backend):
        inv = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="simple")
        assert inv["parameters"].get("nonexistent_key") is None

    def test_inventory_simple_target_comprehensive(self, reclass_compatible_backend):
        """Validate the ``simple`` target which exercises class inheritance,
        scalar override, and dict merging across multiple included classes."""
        inv = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="simple")
        params = inv["parameters"]
        # common.yml sets app_name to "reclass-test", components/app.yml overrides to "myapp"
        assert params["app_name"] == "myapp"
        # components/db.yml
        assert params["db_host"] == "localhost"
        assert params["db_port"] == 5432
        # dict merge: components/app.yml config overrides
        assert params["config"]["port"] == 8080
        assert params["config"]["timeout"] == 30


class TestReclassSpecificFeatures:
    """Tests that only apply to the Python ``reclass`` backend."""

    def test_inventory_exports(self):
        _skip_if_backend_missing(InventoryBackends.RECLASS)
        _set_backend_args(InventoryBackends.RECLASS)
        inv = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="advanced")
        assert "exported_app_name" in inv["exports"]
        assert inv["exports"]["exported_app_name"] == "reclass-test"
        assert "exported_config" in inv["exports"]
        assert inv["exports"]["exported_config"]["log_level"] == "info"


class TestReclassRsSpecificFeatures:
    """Tests documenting known differences in the Rust ``reclass-rs`` backend."""

    def test_inventory_exports_empty(self):
        """Document known difference: reclass-rs may return empty exports."""
        _skip_if_backend_missing(InventoryBackends.RECLASS_RS)
        _set_backend_args(InventoryBackends.RECLASS_RS)
        inv = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="advanced")
        # Reclass-rs currently returns empty exports for this example.
        # This is a known difference from the Python reclass backend.
        assert inv["exports"] == {}

    def test_reclass_rs_compatible_with_reclass(self):
        """Assert that reclass-rs produces the same output as reclass where expected."""
        _skip_if_backend_missing(InventoryBackends.RECLASS_RS)
        _set_backend_args(InventoryBackends.RECLASS_RS)
        inv_rs = get_inventory(inventory_path=RECLASS_INVENTORY, target_name="simple")
        _set_backend_args(InventoryBackends.RECLASS)
        inv_reclass = get_inventory(
            inventory_path=RECLASS_INVENTORY, target_name="simple"
        )
        assert inv_rs["parameters"]["app_name"] == inv_reclass["parameters"]["app_name"]
        assert inv_rs["parameters"]["tags"] == inv_reclass["parameters"]["tags"]
        assert inv_rs["parameters"]["config"] == inv_reclass["parameters"]["config"]
        assert inv_rs["parameters"]["db_host"] == inv_reclass["parameters"]["db_host"]


class TestOmegaconfExampleInventory:
    """Tests for the omegaconf-native example inventory."""

    def test_inventory_targets_discovered(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY)
        assert "basic" in inv
        assert "advanced" in inv
        assert "compile-test" in inv

    def test_inventory_interpolation(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="basic")
        params = inv["parameters"]
        assert params["interpolated"] == "omegaconf-test"
        assert params["nested_interpolated"] == "dev"
        assert params["full_name"] == "omegaconf-test-dev"
        assert params["ref_value"] == "default"

    def test_inventory_escaped_interpolation(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="basic")
        # ${escape:app_name} should produce literal ${app_name}
        assert inv["parameters"]["escaped_value"] == "${app_name}"

    def test_inventory_deferred_interpolation(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="basic")
        # \${app_name} is unescaped in first pass, resolved in second pass
        assert inv["parameters"]["deferred_value"] == "omegaconf-test"

    def test_inventory_merge_resolver(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        # merged_service combines base_service and service_override
        assert params["merged_service"]["type"] == "ClusterIP"
        assert params["merged_service"]["port"] == 8080
        assert params["merged_service"]["target_port"] == 8080
        assert params["merged_service"]["protocol"] == "TCP"

    def test_inventory_deep_merge(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        merged = inv["parameters"]["merged_config"]
        assert merged["level1"]["key_a"] == "value_a"
        assert merged["level1"]["key_b"] == "overridden_b"
        assert merged["level1"]["key_c"] == "value_c"

    def test_inventory_list_concatenation(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        merged = inv["parameters"]["merged_list"]
        assert merged["items"] == ["item1", "item2", "item3", "item4"]

    def test_inventory_conditional_resolvers(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["conditional_result"] == "enabled_value"
        assert params["conditional_else"] == "development_mode"

    def test_inventory_conditional_false(self, omegaconf_backend):
        """${if:} with a false condition should return an empty dict."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="basic")
        assert inv["parameters"]["conditional_false"] == {}

    def test_inventory_escape_does_not_resolve_real_key(self, omegaconf_backend):
        """${escape:} must produce a literal even when the content matches a real key."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="basic")
        assert inv["parameters"]["escaped_real_key"] == "${environment}"
        assert inv["parameters"]["escaped_real_key"] != inv["parameters"]["environment"]

    def test_inventory_arithmetic_resolver(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["computed_replicas"] == 2

    def test_inventory_custom_resolvers(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["custom_concat"] == "helloworld"
        assert params["custom_double"] == 2

    def test_inventory_init_class(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["init_value"] == "from_init"
        assert inv["parameters"]["init_common"] is True

    def test_inventory_target_name(self, omegaconf_backend):
        inv = get_inventory(
            inventory_path=OMEGACONF_INVENTORY, target_name="compile-test"
        )
        assert inv["parameters"]["target_name"] == "compile-test"

    def test_omegaconf_kapitan_metadata_structure(self, omegaconf_backend):
        """Verify ``parameters._kapitan_.name`` exposes ``short``/``full``/
        ``path``/``parts`` for an omegaconf-backed target.

        Replaces the field-by-field assertions from the removed
        ``test_load_and_resolve_single_target`` test in ``test_omegaconf.py``.
        """
        inv = get_inventory(
            inventory_path=OMEGACONF_INVENTORY, target_name="compile-test"
        )
        metadata = inv["parameters"]["_kapitan_"]
        assert metadata == {
            "name": {
                "short": "compile-test",
                "full": "compile-test",
                "path": "compile-test",
                "parts": ["compile-test"],
            }
        }

    def test_omegaconf_three_way_merge(self, omegaconf_backend):
        """Verify a three-way ``${merge:}`` combines defaults, a scalar
        override, and an annotation-style nested addition.

        Replaces the removed ``test_three_way_merge`` case from
        ``test_omegaconf.py``.
        """
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        merged = inv["parameters"]["merged_deployment"]
        # Overridden by deployment_custom (second layer)
        assert merged["replicas"] == 3
        # Preserved from deployment_defaults (first layer)
        assert merged["strategy"]["type"] == "RollingUpdate"
        assert merged["strategy"]["rollingUpdate"]["maxSurge"] == 1
        # Merged annotations: first layer's key survives, third layer adds another
        assert merged["pod_annotations"]["prometheus.io/scrape"] == "true"
        assert merged["pod_annotations"]["custom.io/annotation"] == "test-value"

    def test_inventory_overwrite_behaviour(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        result = inv["parameters"]["overwrite_result"]
        assert result["key_a"] == "value_a"
        assert result["key_b"] == "value_b"
        assert result["nested"]["child"] == "replaced"
        assert result["key_c"] == "value_c"

    def test_inventory_relative_class(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["relative_value"] == "from_relative"
        assert inv["parameters"]["relative_demo"] is True

    def test_inventory_missing_key_returns_none(self, omegaconf_backend):
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="basic")
        assert inv["parameters"].get("nonexistent_key") is None

    def test_inventory_greeting_with_escape(self, omegaconf_backend):
        """Validate that ${escape:...} works mid-string."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        greeting = inv["parameters"]["greeting"]
        assert greeting == "Hello ${USER}, welcome to omegaconf-test"

    def test_inventory_relpath_resolver(self, omegaconf_backend):
        """Test ${relpath:} resolver with nested structures."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="basic")
        params = inv["parameters"]
        assert params["nested_config"]["database"]["host"] == "db.minikube.local"
        assert params["nested_config"]["database"]["port"] == 5432
        assert (
            params["nested_config"]["connection_string"]
            == "postgresql://db.minikube.local:5432/mydb"
        )

    def test_inventory_parentkey_resolver(self, omegaconf_backend):
        """Test ${parentkey:} deferred resolver resolves at definition location."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        deployments = inv["parameters"]["deployments"]
        # parentkey resolves to the original definition key, not merge destination
        assert deployments["web-app"]["name"] == "deployment_template"
        assert deployments["api-service"]["name"] == "deployment_template"
        # In nested labels, parentkey resolves to immediate parent key
        assert deployments["web-app"]["labels"]["app.kubernetes.io/name"] == "labels"

    def test_inventory_custom_resolvers_extended(self, omegaconf_backend):
        """Test get_suffix and get_substr custom resolvers."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        # get_suffix extracts last part of hyphenated string
        assert params["suffix_test"] == "omegaconf-demo".split("-")[-1]
        # get_substr extracts specified index
        assert params["substr_test"] == "omegaconf"

    def test_inventory_upper_resolver(self, omegaconf_backend):
        """Test ${upper:} custom resolver converts to uppercase."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["uppercase_test"]["env_upper"] == "DEV"
        assert params["uppercase_test"]["cluster_upper"] == "MINIKUBE"

    def test_inventory_capitalize_resolver(self, omegaconf_backend):
        """Test ${capitalize:} custom resolver for camelCase conversion."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["capitalize_test"]["camel_name"] == "omegaconfTest"

    def test_inventory_root_context_resolver(self, omegaconf_backend):
        """Test custom resolver using _root_ to access target_name."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["secrets"]["db_password"] == "advanced/database/password"

    def test_inventory_empty_class_handling(self, omegaconf_backend):
        """Test that classes with null/empty values are handled correctly."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["empty_test"]["loaded"] is True

    def test_inventory_remove_config(self, omegaconf_backend):
        """Test that omegaconf.remove configuration lists multiple keys."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert "omegaconf" in params
        assert "remove" in params["omegaconf"]
        remove_list = params["omegaconf"]["remove"]
        assert "base_component" in remove_list
        assert "service_defaults" in remove_list
        assert "deployment_defaults" in remove_list

    def test_inventory_list_resolver(self, omegaconf_backend):
        """Test ${list:} resolver converts dict to list of single-key dicts."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        result = inv["parameters"]["list_result"]
        assert {"item1": "first"} in result
        assert {"item2": "second"} in result

    def test_inventory_yaml_resolver(self, omegaconf_backend):
        """Test ${yaml:} resolver dumps nested structure to YAML string."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        result = inv["parameters"]["yaml_result"]
        assert "level1:" in result
        assert "level2: nested_value" in result

    def test_inventory_default_resolver(self, omegaconf_backend):
        """Test ${default:} resolver provides fallback for missing key."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["default_result"] == "fallback_value"

    def test_inventory_access_resolver(self, omegaconf_backend):
        """Test ${access:} resolver accesses a key containing dots."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["access_result"] == "accessed_value"

    def test_inventory_boolean_resolvers(self, omegaconf_backend):
        """Test ${and:}, ${or:}, ${not:}, ${equal:} boolean algebra resolvers."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["bool_and"] is False
        assert params["bool_or"] is True
        assert params["bool_not"] is False
        assert params["bool_equal"] is True

    def test_inventory_key_resolvers(self, omegaconf_backend):
        """Test ${key:} and ${fullkey:} resolvers return key names."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        key_test = inv["parameters"]["key_test"]
        assert key_test["simple_name"] == "simple_name"
        assert "key_test" in key_test["full_name"]

    def test_inventory_write_resolver(self, omegaconf_backend):
        """Test ${write:} resolver copies content to another location in inventory."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        params = inv["parameters"]
        assert params["write_result"] == "DONE"
        written = params["written_target"]
        assert written["copied"] is True
        assert written["nested"]["value"] == "written_value"

    def test_inventory_nested_function_composition(self, omegaconf_backend):
        """Test nested resolver composition ${upper:${concat:hello,world}}."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["nested_func"] == "HELLOWORLD"

    def test_inventory_parentkey_simple(self, omegaconf_backend):
        """Test ${parentkey:} in non-deferred context resolves to immediate parent."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["parentkey_test"]["name"] == "parentkey_test"

    def test_inventory_if_numeric_condition(self, omegaconf_backend):
        """Test ${if:} with a numeric (truthy) condition."""
        inv = get_inventory(inventory_path=OMEGACONF_INVENTORY, target_name="advanced")
        assert inv["parameters"]["if_numeric"] == "has_replicas"


class TestBackendExampleGoldenOutput:
    """Golden-master compile tests for backend examples.

    These tests compile the backend examples and compare the full compiled
    output tree against committed golden snapshots. A unified diff is
    produced on mismatch so reviewers see exactly which files changed.

    To update golden snapshots after an intentional output change:
        make refresh-backend-goldens
    """

    def test_reclass_example_golden_output(self):
        _skip_if_backend_missing(InventoryBackends.RECLASS)
        with IsolatedTestEnvironment(RECLASS_EXAMPLE) as iso:
            exit_code, _, stderr = run_kapitan_command(
                [
                    "compile",
                    "--inventory-path",
                    "inventory",
                    f"--inventory-backend={InventoryBackends.RECLASS}",
                ]
            )
            assert exit_code == 0, stderr
            from tests.test_helpers import assert_directories_match

            assert_directories_match(
                os.path.join(iso.path, "compiled"),
                os.path.join(TEST_PWD, "tests/golden/backend_examples/reclass"),
            )

    def test_reclass_rs_example_golden_output(self):
        _skip_if_backend_missing(InventoryBackends.RECLASS_RS)
        with IsolatedTestEnvironment(RECLASS_EXAMPLE) as iso:
            exit_code, _, stderr = run_kapitan_command(
                [
                    "compile",
                    "--inventory-path",
                    "inventory",
                    f"--inventory-backend={InventoryBackends.RECLASS_RS}",
                ]
            )
            assert exit_code == 0, stderr
            from tests.test_helpers import assert_directories_match

            assert_directories_match(
                os.path.join(iso.path, "compiled"),
                os.path.join(TEST_PWD, "tests/golden/backend_examples/reclass-rs"),
            )

    def test_omegaconf_example_golden_output(self, omegaconf_backend):
        with IsolatedTestEnvironment(OMEGACONF_EXAMPLE) as iso:
            exit_code, _, stderr = run_kapitan_command(
                [
                    "compile",
                    "--inventory-path",
                    "inventory",
                    f"--inventory-backend={InventoryBackends.OMEGACONF}",
                ]
            )
            assert exit_code == 0, stderr
            from tests.test_helpers import assert_directories_match

            assert_directories_match(
                os.path.join(iso.path, "compiled"),
                os.path.join(TEST_PWD, "tests/golden/backend_examples/omegaconf"),
            )
