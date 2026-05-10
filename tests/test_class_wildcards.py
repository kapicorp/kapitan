#!/usr/bin/env python3

# Copyright 2026 The Kapitan Authors
# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for wildcard class expansion in inventory ``classes:`` lists.

Implements the feature requested in kapicorp/kapitan#1084.
"""

import importlib.util
import os
import tempfile
import unittest

import yaml

from kapitan.errors import InventoryError
from kapitan.inventory.backends.reclass import ReclassInventory
from kapitan.inventory.wildcards import (
    discover_classes,
    expand_class_patterns,
    is_pattern,
)


def _backend_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _make_reclass_rs_inventory(inv_path: str, ignore_missing: bool = False):
    from kapitan.inventory.backends.reclass_rs import ReclassRsInventory

    return ReclassRsInventory(
        inventory_path=inv_path, ignore_class_not_found=ignore_missing
    )


def _make_omegaconf_inventory(inv_path: str, ignore_missing: bool = False):
    from kapitan.inventory.backends.omegaconf import OmegaConfInventory

    return OmegaConfInventory(
        inventory_path=inv_path, ignore_class_not_found=ignore_missing
    )


def _write(path: str, data: dict | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data or {}, fh)


def _build_inventory(root: str, files: dict, target_classes: list) -> str:
    """Create a minimal inventory under ``root`` with the given class files
    and a single target ``example`` referencing ``target_classes``.
    Returns the inventory path.
    """
    inv = os.path.join(root, "inventory")
    classes_dir = os.path.join(inv, "classes")
    targets_dir = os.path.join(inv, "targets")
    os.makedirs(classes_dir, exist_ok=True)
    os.makedirs(targets_dir, exist_ok=True)
    for relpath, content in files.items():
        _write(os.path.join(classes_dir, relpath), content)
    _write(
        os.path.join(targets_dir, "example.yml"),
        {"classes": target_classes, "parameters": {}},
    )
    return inv


class IsPatternTest(unittest.TestCase):
    def test_plain_names_are_not_patterns(self):
        self.assertFalse(is_pattern("common"))
        self.assertFalse(is_pattern("clusters.prod"))
        self.assertFalse(is_pattern("dev-common"))

    def test_glob_metacharacters_make_patterns(self):
        self.assertTrue(is_pattern("*"))
        self.assertTrue(is_pattern("clusters.*"))
        self.assertTrue(is_pattern("dev-*"))
        self.assertTrue(is_pattern("foo?"))
        self.assertTrue(is_pattern("foo[12]"))


class DiscoverClassesTest(unittest.TestCase):
    def test_discovers_yml_and_yaml_skips_hidden_and_non_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            classes = os.path.join(tmp, "classes")
            _write(os.path.join(classes, "common.yml"))
            _write(os.path.join(classes, "clusters", "prod.yml"))
            _write(os.path.join(classes, "clusters", "dev.yaml"))
            _write(os.path.join(classes, "foo", "init.yml"))
            _write(os.path.join(classes, ".secret.yml"))
            with open(os.path.join(classes, "README.md"), "w") as fh:
                fh.write("readme")
            with open(os.path.join(classes, "tmp.json"), "w") as fh:
                fh.write("{}")

            found = discover_classes(classes)
            self.assertEqual(
                found,
                ["clusters.dev", "clusters.prod", "common", "foo"],
            )

    def test_root_init_yml_maps_to_init(self):
        """classes/init.yml must be discoverable as class name 'init'."""
        with tempfile.TemporaryDirectory() as tmp:
            classes = os.path.join(tmp, "classes")
            _write(os.path.join(classes, "init.yml"))
            _write(os.path.join(classes, "common.yml"))
            _write(os.path.join(classes, "foo", "init.yml"))

            found = discover_classes(classes)
            self.assertEqual(found, ["common", "foo", "init"])

    def test_missing_classes_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(discover_classes(os.path.join(tmp, "missing")), [])


class ExpandClassPatternsTest(unittest.TestCase):
    AVAILABLE = [
        "common",
        "clusters.prod",
        "clusters.dev",
        "services.api",
        "dev-common",
        "apps.dev-api",
        "apps.prod-api",
    ]

    def test_exact_names_are_unchanged(self):
        out = expand_class_patterns(["common"], self.AVAILABLE)
        self.assertEqual(out, ["common"])

    def test_star_matches_all(self):
        out = expand_class_patterns(["*"], self.AVAILABLE)
        self.assertEqual(out, sorted(self.AVAILABLE))

    def test_directory_pattern_matches_full_name(self):
        out = expand_class_patterns(["clusters.*"], self.AVAILABLE)
        self.assertEqual(out, ["clusters.dev", "clusters.prod"])

    def test_basename_pattern_matches_in_all_subdirectories(self):
        out = expand_class_patterns(["dev-*"], self.AVAILABLE)
        self.assertEqual(out, ["apps.dev-api", "dev-common"])

    def test_mixed_entries_preserve_order_and_deduplicate(self):
        out = expand_class_patterns(
            ["common", "clusters.*", "common", "clusters.prod"],
            self.AVAILABLE,
        )
        # exact `common` first (kept in place); then sorted clusters.*
        # expansion; later duplicates of `common` and `clusters.prod`
        # are dropped.
        self.assertEqual(out, ["common", "clusters.dev", "clusters.prod"])

    def test_unmatched_pattern_raises_inventory_error(self):
        with self.assertRaises(InventoryError):
            expand_class_patterns(["missing-*"], self.AVAILABLE)

    def test_unmatched_pattern_silenced_when_ignore_flag_set(self):
        out = expand_class_patterns(
            ["common", "missing-*"],
            self.AVAILABLE,
            ignore_class_not_found=True,
        )
        self.assertEqual(out, ["common"])

    def test_exact_missing_name_is_not_intercepted(self):
        # exact (non-pattern) names that are not in `available` are passed
        # through unchanged so the underlying inventory backend can apply
        # its own missing-class handling.
        out = expand_class_patterns(["missing"], self.AVAILABLE)
        self.assertEqual(out, ["missing"])


class _WildcardIntegrationMixin:
    """End-to-end integration tests reusable across inventory backends."""

    inventory_factory = staticmethod(
        lambda inv_path, ignore_missing=False: ReclassInventory(
            inventory_path=inv_path, ignore_class_not_found=ignore_missing
        )
    )

    def _render(self, inv_path: str, ignore_missing: bool = False):
        inv = self.inventory_factory(inv_path, ignore_missing=ignore_missing)
        return list(inv.targets["example"].classes)

    def test_exact_class_name_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "common.yml": {"parameters": {"a": 1}},
                    "base/init.yml": {"parameters": {"b": 2}},
                },
                ["common"],
            )
            self.assertIn("common", self._render(inv))

    def test_star_expands_to_all_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "common.yml": {},
                    "clusters/prod.yml": {},
                    "clusters/dev.yml": {},
                    "services/api.yml": {},
                },
                ["*"],
            )
            self.assertEqual(
                sorted(self._render(inv)),
                ["clusters.dev", "clusters.prod", "common", "services.api"],
            )

    def test_directory_pattern_expansion(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "common.yml": {},
                    "clusters/prod.yml": {},
                    "clusters/dev.yml": {},
                },
                ["clusters.*"],
            )
            rendered = self._render(inv)
            self.assertEqual(sorted(rendered), ["clusters.dev", "clusters.prod"])
            self.assertNotIn("common", rendered)

    def test_basename_prefix_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "dev-common.yml": {},
                    "apps/dev-api.yml": {},
                    "apps/prod-api.yml": {},
                },
                ["dev-*"],
            )
            rendered = self._render(inv)
            self.assertEqual(sorted(rendered), ["apps.dev-api", "dev-common"])
            self.assertNotIn("apps.prod-api", rendered)

    def test_yaml_extension_supported(self):
        # The omegaconf backend's class file resolver only looks for .yml
        # files (pre-existing limitation, unrelated to wildcards), so we
        # only assert that wildcard expansion *discovers* the .yaml class.
        if "OmegaConf" in type(self).__name__:
            self.skipTest("omegaconf backend does not load .yaml files (pre-existing)")
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {"clusters/prod.yaml": {}},
                ["clusters.*"],
            )
            self.assertIn("clusters.prod", self._render(inv))

    def test_combined_example_from_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "common.yml": {},
                    "clusters/prod.yml": {},
                    "clusters/dev.yml": {},
                    "apps/dev-api.yml": {},
                    "apps/prod-api.yml": {},
                },
                ["common", "clusters.*", "dev-*"],
            )
            rendered = self._render(inv)
            self.assertEqual(
                sorted(rendered),
                ["apps.dev-api", "clusters.dev", "clusters.prod", "common"],
            )
            self.assertNotIn("apps.prod-api", rendered)

    def test_unmatched_pattern_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {"common.yml": {}},
                ["missing-*"],
            )
            with self.assertRaises(InventoryError):
                self._render(inv)

    def test_unmatched_pattern_ignored_with_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {"common.yml": {}},
                ["common", "missing-*"],
            )
            rendered = self._render(inv, ignore_missing=True)
            self.assertIn("common", rendered)

    def test_wildcard_in_nested_class_is_expanded(self):
        """Wildcards inside class files (not just targets) must also be expanded."""
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "umbrella.yml": {"classes": ["clusters.*"]},
                    "clusters/prod.yml": {},
                    "clusters/dev.yml": {},
                },
                ["umbrella"],
            )
            rendered = self._render(inv)
            self.assertIn("umbrella", rendered)
            self.assertIn("clusters.prod", rendered)
            self.assertIn("clusters.dev", rendered)


class ReclassWildcardIntegrationTest(_WildcardIntegrationMixin, unittest.TestCase):
    inventory_factory = staticmethod(
        lambda inv_path, ignore_missing=False: ReclassInventory(
            inventory_path=inv_path, ignore_class_not_found=ignore_missing
        )
    )

    def test_original_inventory_path_is_preserved(self):
        """``Inventory.original_inventory_path`` must point at the user's
        inventory even when wildcard expansion materialized a temp copy.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {}, "clusters/prod.yml": {}},
                ["clusters.*"],
            )
            inv = ReclassInventory(inventory_path=inv_path)
            self.assertEqual(inv.original_inventory_path, inv_path)
            # Materialization happened — backend path differs from original.
            self.assertNotEqual(inv.inventory_path, inv_path)

    def test_no_wildcards_means_no_materialization(self):
        """When no wildcard entries exist, ``inventory_path`` must remain
        the original path (zero overhead path).
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {}},
                ["common"],
            )
            inv = ReclassInventory(inventory_path=inv_path)
            self.assertEqual(inv.inventory_path, inv_path)
            self.assertEqual(inv.original_inventory_path, inv_path)


@unittest.skipUnless(_backend_available("reclass_rs"), "reclass_rs not available")
class ReclassRsWildcardIntegrationTest(_WildcardIntegrationMixin, unittest.TestCase):
    inventory_factory = staticmethod(_make_reclass_rs_inventory)


@unittest.skipUnless(_backend_available("omegaconf"), "omegaconf not available")
class OmegaConfWildcardIntegrationTest(_WildcardIntegrationMixin, unittest.TestCase):
    inventory_factory = staticmethod(_make_omegaconf_inventory)


if __name__ == "__main__":
    unittest.main()
