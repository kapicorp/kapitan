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
import shutil
import tempfile
import unittest

import yaml

from kapitan.errors import InventoryError
from kapitan.inventory.backends.reclass import ReclassInventory
from kapitan.inventory.wildcards import (
    _fix_relative_symlinks,
    discover_classes,
    expand_class_patterns,
    is_pattern,
    materialize_expanded_inventory,
)


def _backend_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _make_reclass_rs_inventory(inv_path: str, ignore_missing: bool = False):
    from kapitan.inventory.backends.reclass_rs import ReclassRsInventory

    return ReclassRsInventory(
        inventory_path=inv_path,
        ignore_class_not_found=ignore_missing,
        enable_class_wildcards=True,
    )


def _make_omegaconf_inventory(inv_path: str, ignore_missing: bool = False):
    from kapitan.inventory.backends.omegaconf import OmegaConfInventory

    return OmegaConfInventory(
        inventory_path=inv_path,
        ignore_class_not_found=ignore_missing,
        enable_class_wildcards=True,
    )


def _write(path: str, data: dict | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data or {}, fh)


def _build_inventory(
    root: str, files: dict, target_classes: list, target_params: dict | None = None
) -> str:
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
        {"classes": target_classes, "parameters": target_params or {}},
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

    def test_reclass_reference_looks_like_pattern(self):
        """A Reclass reference like ${?var} contains ? and is_pattern returns
        True for it.  This is precisely why enable_class_wildcards defaults to
        False: such references must NOT be treated as glob patterns.
        """
        self.assertTrue(is_pattern("${?some_parameter}"))
        self.assertTrue(is_pattern("*anchor"))


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

    def test_circular_symlink_is_detected_and_pruned(self):
        """Circular directory symlinks must not cause infinite recursion."""
        with tempfile.TemporaryDirectory() as tmp:
            classes = os.path.join(tmp, "classes")
            os.makedirs(os.path.join(classes, "a"))
            _write(os.path.join(classes, "a", "x.yml"))
            # Create circular symlink: classes/a/b -> ../a
            os.symlink(os.path.join("..", "a"), os.path.join(classes, "a", "b"))

            found = discover_classes(classes)
            self.assertEqual(found, ["a.x"])


class ExpandClassPatternsTest(unittest.TestCase):
    AVAILABLE = [
        "common",
        "clusters.prod",
        "clusters.dev",
        "services.api",
        "dev-common",
        "apps.dev-api",
        "apps.prod-api",
        "config[html]",
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

    def test_basename_pattern_only_matches_top_level_full_name(self):
        """With the simplified full-dotted-name semantics, ``dev-*`` matches
        ONLY top-level class names starting with 'dev-' (not nested ones
        like ``apps.dev-api``).  Users who want basename-style matching in
        subdirectories must write ``*.dev-*`` explicitly.
        """
        out = expand_class_patterns(["dev-*"], self.AVAILABLE)
        self.assertEqual(out, ["dev-common"])

    def test_glob_in_nested_dirs_requires_explicit_prefix(self):
        out = expand_class_patterns(["*.dev-*"], self.AVAILABLE)
        self.assertEqual(out, ["apps.dev-api"])

    def test_reclass_reference_passed_through_unchanged(self):
        """A class entry that looks like a Reclass / Kapitan reference
        (e.g. ``${some_var}`` or ``${?optional}``) must be preserved
        verbatim and never matched as a glob, even when it contains ``?``.
        """
        out = expand_class_patterns(
            ["common", "${?some_var}", "${other_var}"], self.AVAILABLE
        )
        self.assertEqual(out, ["common", "${?some_var}", "${other_var}"])

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

    def test_expansion_order_is_lexicographic(self):
        """Pattern expansion is lexicographic.  'config' sorts before
        'defaults', so a wildcard like '*.base' can produce a surprising
        include order: config.base appears before defaults.base.
        Users must name matching classes carefully when order matters.
        """
        available = ["defaults.base", "config.base"]
        out = expand_class_patterns(["*.base"], available)
        # lexicographic: 'c' < 'd'
        self.assertEqual(out, ["config.base", "defaults.base"])
        self.assertLess(out.index("config.base"), out.index("defaults.base"))

    def test_exact_match_takes_precedence_over_pattern(self):
        """If a classes: entry exactly matches an existing class name, it
        must be treated as a literal include even when the name contains
        glob metacharacters.  This is critical for backward compatibility
        with inventories that have class files like ``config[html].yml``.
        """
        out = expand_class_patterns(["config[html]"], self.AVAILABLE)
        self.assertEqual(out, ["config[html]"])

    def test_exact_match_precedence_avoids_fnmatch_interpretation(self):
        """``config[html]`` as a fnmatch pattern would mean 'config'
        followed by a single character from the set {h,t,m,l}.  The string
        ``config[html]`` does NOT match that pattern, so without exact-match
        precedence it would silently error (or be ignored).  Exact-match
        precedence ensures the class is included literally.
        """
        out = expand_class_patterns(["config[html]"], self.AVAILABLE)
        self.assertIn("config[html]", out)
        self.assertEqual(len(out), 1)

    def test_exact_match_precedence_does_not_block_real_patterns(self):
        """When an entry does NOT match any existing class exactly, it is
        still expanded as a pattern if it contains metacharacters.
        """
        out = expand_class_patterns(["apps.*"], self.AVAILABLE)
        self.assertEqual(out, ["apps.dev-api", "apps.prod-api"])

    def test_literal_asterisk_class_name_with_precedence(self):
        available = ["common", "config*special", "config.normal"]
        out = expand_class_patterns(["config*special"], available)
        self.assertEqual(out, ["config*special"])

    def test_literal_question_mark_class_name_with_precedence(self):
        available = ["common", "what?", "whatis"]
        out = expand_class_patterns(["what?"], available)
        self.assertEqual(out, ["what?"])

    def test_non_string_entries_are_ignored(self):
        """Non-string entries in a ``classes:`` list (e.g. integers, None,
        booleans) must be skipped gracefully rather than crashing.
        """
        out = expand_class_patterns(
            ["common", 1, None, True, "*"],
            ["common", "foo", "bar"],
        )
        self.assertEqual(out, ["common", "bar", "foo"])


class FixRelativeSymlinksTest(unittest.TestCase):
    def test_broken_relative_external_symlink_rewritten_to_absolute(self):
        """A relative symlink pointing outside the inventory tree breaks in
        a copied tree because the relative base changes.  _fix_relative_symlinks
        should rewrite it to an absolute path.
        """
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src")
            # Place dest deeper so the same relative path no longer resolves.
            dest = os.path.join(tmp, "nested", "dest")
            external = os.path.join(tmp, "external")
            os.makedirs(os.path.join(src, "classes"))
            os.makedirs(external)
            _write(os.path.join(external, "ext.yml"), {"parameters": {"x": 1}})

            # Relative symlink from src/classes/ext -> ../../external
            os.symlink(
                os.path.relpath(external, os.path.join(src, "classes")),
                os.path.join(src, "classes", "ext"),
            )

            shutil.copytree(src, dest, symlinks=True)
            # The copied relative symlink is now broken because dest is nested.
            self.assertFalse(os.path.exists(os.path.join(dest, "classes", "ext")))

            _fix_relative_symlinks(src, dest)
            # After fixing, it should resolve to the external dir.
            self.assertTrue(os.path.exists(os.path.join(dest, "classes", "ext")))
            self.assertTrue(os.path.islink(os.path.join(dest, "classes", "ext")))

    def test_internal_relative_symlink_left_untouched(self):
        """Relative symlinks that stay inside the copied tree should not be
        rewritten.
        """
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src")
            dest = os.path.join(tmp, "dest")
            os.makedirs(os.path.join(src, "classes", "a"))
            _write(os.path.join(src, "classes", "a", "x.yml"))
            os.symlink(
                os.path.join("a", "x.yml"),
                os.path.join(src, "classes", "b.yml"),
            )

            shutil.copytree(src, dest, symlinks=True)
            _fix_relative_symlinks(src, dest)

            link_target = os.readlink(os.path.join(dest, "classes", "b.yml"))
            self.assertEqual(link_target, os.path.join("a", "x.yml"))


class MaterializeExpandedInventoryTest(unittest.TestCase):
    """Tests for materialize_expanded_inventory() focusing on the opt-in gate
    and on edge-cases around metacharacters in non-class YAML values.
    """

    def test_returns_original_path_when_wildcards_disabled(self):
        """When enable_wildcards=False (default), no materialization occurs
        regardless of what metacharacters appear in the inventory files.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"clusters/prod.yml": {}, "clusters/dev.yml": {}},
                ["clusters.*"],
            )
            result = materialize_expanded_inventory(inv_path, enable_wildcards=False)
            self.assertEqual(result, inv_path)

    def test_returns_different_path_when_wildcards_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"clusters/prod.yml": {}, "clusters/dev.yml": {}},
                ["clusters.*"],
            )
            result = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            self.assertNotEqual(result, inv_path)

    def test_metachar_in_parameters_does_not_trigger_expansion(self):
        """A YAML file that contains * or [ in parameter values (e.g. an
        AWS ARN) but NOT in its classes: list must not cause materialization.
        The cheap text scan may read the file, but after parsing the classes
        list it finds no patterns and returns the original path unchanged.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {"parameters": {"arn": "arn:aws:s3:::my-bucket/*"}}},
                ["common"],
            )
            result = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            # No pattern in classes: -> no materialization
            self.assertEqual(result, inv_path)

    def test_kapitan_secret_ref_in_parameters_does_not_trigger_expansion(self):
        """A Kapitan secret reference ?{plain:some/secret} in a parameter
        value must not trigger wildcard expansion of the classes: list.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {"parameters": {"ref": "?{plain:some/secret}"}}},
                ["common"],
            )
            result = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            self.assertEqual(result, inv_path)

    def test_symlink_to_file_within_inventory_tree_is_preserved(self):
        """A symlink to a *file* inside the inventory tree is listed by
        os.walk and survives materialization as a symlink.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"clusters/prod.yml": {}, "clusters/dev.yml": {}},
                ["clusters.*"],
            )
            # Create a file symlink: classes/aliases/dev_alias.yml -> ../clusters/dev.yml
            aliases_dir = os.path.join(inv_path, "classes", "aliases")
            os.makedirs(aliases_dir)
            os.symlink(
                os.path.join("..", "clusters", "dev.yml"),
                os.path.join(aliases_dir, "dev_alias.yml"),
            )

            dest = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            dest_symlink = os.path.join(dest, "classes", "aliases", "dev_alias.yml")
            self.assertTrue(os.path.islink(dest_symlink))
            # The symlink target is relative within the tree and still resolves
            self.assertTrue(os.path.exists(dest_symlink))

    def test_relative_directory_symlink_outside_inventory_is_rewritten(self):
        """A relative symlink to an external directory is broken after a
        copy because the relative base changes.  Materialization must rewrite
        such symlinks to absolute paths so the classes inside remain loadable.
        """
        with tempfile.TemporaryDirectory() as tmp:
            external = os.path.join(tmp, "external_classes")
            os.makedirs(external)
            _write(os.path.join(external, "ext_class.yml"), {"parameters": {"x": 1}})

            inv_path = _build_inventory(tmp, {}, ["ext.*"])
            # Relative symlink: inventory/classes/ext -> ../../external_classes
            symlink_path = os.path.join(inv_path, "classes", "ext")
            rel_target = os.path.relpath(external, os.path.join(inv_path, "classes"))
            os.symlink(rel_target, symlink_path)

            # Without rewriting, the symlink would be broken in the temp copy.
            dest = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            dest_symlink = os.path.join(dest, "classes", "ext")
            self.assertTrue(os.path.islink(dest_symlink))
            self.assertTrue(os.path.exists(dest_symlink))

            # The symlinked class should now be discoverable and match the pattern.
            from kapitan.inventory.wildcards import discover_classes

            found = discover_classes(os.path.join(dest, "classes"))
            self.assertIn("ext.ext_class", found)

    def test_empty_classes_list_does_not_trigger_materialization(self):
        """An empty ``classes: []`` list must not cause materialization."""
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(tmp, {"common.yml": {}}, [])
            result = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            self.assertEqual(result, inv_path)

    def test_classes_list_with_only_references_does_not_trigger_materialization(self):
        """A ``classes:`` list containing only Reclass references and no
        glob metacharacters must not cause materialization."""
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(tmp, {"common.yml": {}}, ["${a}", "${b}"])
            result = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            self.assertEqual(result, inv_path)

    def test_nonexistent_path_returns_unchanged(self):
        result = materialize_expanded_inventory(
            "/nonexistent/path", enable_wildcards=True
        )
        self.assertEqual(result, "/nonexistent/path")

    def test_malformed_yaml_with_metachar_logs_warning(self):
        """A file containing a metacharacter but invalid YAML should log a
        warning rather than crashing or being silently ignored.
        """
        import logging
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            inv = os.path.join(tmp, "inventory")
            os.makedirs(os.path.join(inv, "targets"))
            os.makedirs(os.path.join(inv, "classes"))
            with open(
                os.path.join(inv, "targets", "broken.yml"), "w", encoding="utf-8"
            ) as fh:
                fh.write("classes: [*")  # invalid YAML with metacharacter

            logger = logging.getLogger("kapitan.inventory.wildcards")
            with patch.object(logger, "warning") as mock_warn:
                result = materialize_expanded_inventory(inv, enable_wildcards=True)
                # Should return the original path because the file failed to parse
                self.assertEqual(result, inv)
                mock_warn.assert_called_once()
                self.assertIn("broken.yml", mock_warn.call_args[0][1])


class FeatureFlagTest(unittest.TestCase):
    """Verify opt-in / opt-out semantics at the Inventory level."""

    def test_inventory_default_does_not_expand_wildcards(self):
        """With enable_class_wildcards=False (the default), an inventory that
        contains wildcard patterns in classes: is NOT pre-expanded.  The
        inventory_path attribute must equal the original path.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"clusters/prod.yml": {}, "clusters/dev.yml": {}},
                ["clusters.*"],
            )
            inv = ReclassInventory(
                inventory_path=inv_path,
                enable_class_wildcards=False,
                initialise=False,
            )
            self.assertEqual(inv.inventory_path, inv_path)
            self.assertEqual(inv.original_inventory_path, inv_path)

    def test_inventory_path_unchanged_without_opt_in(self):
        """original_inventory_path and inventory_path are identical when the
        feature flag is off, even if the target references a wildcard pattern.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(tmp, {"common.yml": {}}, ["clusters.*"])
            inv = ReclassInventory(
                inventory_path=inv_path,
                enable_class_wildcards=False,
                initialise=False,
            )
            self.assertEqual(inv.inventory_path, inv_path)

    def test_inventory_materializes_when_opted_in(self):
        """When enable_class_wildcards=True and a wildcard exists in classes:,
        inventory_path points at a temp copy while original_inventory_path
        still points at the user's on-disk inventory.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"clusters/prod.yml": {}, "clusters/dev.yml": {}},
                ["clusters.*"],
            )
            inv = ReclassInventory(
                inventory_path=inv_path,
                enable_class_wildcards=True,
                initialise=False,
            )
            self.assertEqual(inv.original_inventory_path, inv_path)
            self.assertNotEqual(inv.inventory_path, inv_path)


class LiteralMetacharacterCompatibilityTest(unittest.TestCase):
    """Tests proving that the default-off behavior and exact-match precedence
    preserve backwards compatibility for inventories that contain glob-like
    characters in legitimate places (literal class names, parameter values,
    Reclass references).
    """

    def test_literal_bracketed_class_name_loadable_when_flag_disabled(self):
        """A class file literally named ``config[html].yml`` must be
        loadable as the exact class name ``config[html]`` when wildcards
        are disabled (the default).
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"config[html].yml": {"parameters": {"format": "html"}}},
                ["config[html]"],
            )
            # Default: enable_class_wildcards=False
            inv = ReclassInventory(inventory_path=inv_path)
            rendered = list(inv.targets["example"].classes)
            self.assertIn("config[html]", rendered)
            self.assertEqual(inv.inventory_path, inv_path)

    def test_literal_bracketed_class_name_loadable_when_flag_enabled(self):
        """With wildcards enabled, ``config[html]`` must still be treated as
        an exact class include because it matches an existing class file.
        Exact-match precedence prevents it from being misinterpreted as a
        glob pattern.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"config[html].yml": {"parameters": {"format": "html"}}},
                ["config[html]"],
            )
            inv = ReclassInventory(
                inventory_path=inv_path,
                enable_class_wildcards=True,
            )
            rendered = list(inv.targets["example"].classes)
            self.assertIn("config[html]", rendered)

    def test_reclass_reference_in_classes_list_preserved_when_disabled(self):
        """A Reclass reference like ``${?some_var}`` in a classes: list must
        be passed through to the backend untouched when wildcards are off.
        Reclass / reclass-rs will then resolve the reference normally.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {}},
                ["common", "${?some_var}"],
            )
            # No materialization, no rewrite.
            inv = ReclassInventory(
                inventory_path=inv_path,
                ignore_class_not_found=True,
                initialise=False,
            )
            self.assertEqual(inv.inventory_path, inv_path)
            # Read back the target file directly: classes list must be unchanged.
            target_yml = os.path.join(inv_path, "targets", "example.yml")
            with open(target_yml) as fh:
                data = yaml.safe_load(fh)
            self.assertEqual(data["classes"], ["common", "${?some_var}"])

    def test_reclass_reference_preserved_when_wildcards_enabled(self):
        """When wildcards are enabled, an obvious Reclass reference in a
        classes: list (``${...}`` or ``${?...}``) must still be passed
        through unchanged.  The wildcard expander must not try to glob-match
        it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {}, "clusters/prod.yml": {}, "clusters/dev.yml": {}},
                ["clusters.*", "${?some_var}"],
            )
            available = discover_classes(os.path.join(inv_path, "classes"))
            expanded = expand_class_patterns(["clusters.*", "${?some_var}"], available)
            self.assertEqual(
                expanded, ["clusters.dev", "clusters.prod", "${?some_var}"]
            )

    def test_yaml_anchor_in_parameters_does_not_trigger_materialization(self):
        """A YAML anchor / alias in a parameter value (``*ref``) contains ``*``
        but must not cause materialization when wildcards are enabled, because
        the wildcard belongs to a parameter value and not to the classes list.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                # Use a literal string starting with * (we do not need YAML
                # anchor semantics here - the cheap text scan triggers on
                # ANY * in the file).
                {"common.yml": {"parameters": {"alias_value": "*shared_anchor"}}},
                ["common"],
            )
            result = materialize_expanded_inventory(inv_path, enable_wildcards=True)
            self.assertEqual(result, inv_path)


class _WildcardIntegrationMixin:
    """End-to-end integration tests reusable across inventory backends.

    All factories here pass enable_class_wildcards=True so that the wildcard
    feature is exercised.  The opt-in / opt-out path is covered separately in
    FeatureFlagTest and MaterializeExpandedInventoryTest.
    """

    inventory_factory = staticmethod(
        lambda inv_path, ignore_missing=False: ReclassInventory(
            inventory_path=inv_path,
            ignore_class_not_found=ignore_missing,
            enable_class_wildcards=True,
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

    def test_hyphenated_class_names_matched_by_wildcard(self):
        """Hyphenated names like ``nfs-client-provisioner`` are common in
        Project Syn / Commodore repositories.  A prefix pattern must
        match them correctly.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "nfs-client-provisioner.yml": {},
                    "nfs-server.yml": {},
                    "common.yml": {},
                },
                ["nfs-*"],
            )
            rendered = self._render(inv)
            self.assertIn("nfs-client-provisioner", rendered)
            self.assertIn("nfs-server", rendered)
            self.assertNotIn("common", rendered)

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

    def test_explicit_prefix_pattern(self):
        """Patterns are matched against the full dotted class name only.
        ``apps.dev-*`` matches only classes under apps/ starting with 'dev-'.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "dev-common.yml": {},
                    "apps/dev-api.yml": {},
                    "apps/prod-api.yml": {},
                },
                ["apps.dev-*"],
            )
            rendered = self._render(inv)
            self.assertEqual(sorted(rendered), ["apps.dev-api"])
            self.assertNotIn("apps.prod-api", rendered)
            self.assertNotIn("dev-common", rendered)

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
                ["common", "clusters.*", "apps.dev-*"],
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

    def test_expansion_order_matches_lexicographic(self):
        """Classes included via a wildcard appear in the rendered classes list
        in lexicographic order.  'config' sorts before 'defaults', so
        'config.base' precedes 'defaults.base' in the expansion of '*.base'.
        Backend merge semantics determine which value wins; users must name
        classes to ensure desired override order.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "config/base.yml": {"parameters": {"val": "from-config"}},
                    "defaults/base.yml": {"parameters": {"val": "from-defaults"}},
                },
                ["*.base"],
            )
            rendered = self._render(inv)
            self.assertIn("config.base", rendered)
            self.assertIn("defaults.base", rendered)
            # Lexicographic: config.base sorts before defaults.base
            self.assertLess(
                rendered.index("config.base"), rendered.index("defaults.base")
            )

    def test_literal_metacharacter_class_with_wildcards_enabled(self):
        """A class file with metacharacters in its name must be loadable
        even when wildcards are enabled, thanks to exact-match precedence.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv = _build_inventory(
                tmp,
                {
                    "common.yml": {},
                    "config[html].yml": {"parameters": {"format": "html"}},
                },
                ["config[html]"],
            )
            rendered = self._render(inv)
            self.assertIn("config[html]", rendered)

    def test_relative_symlinked_class_directory_works(self):
        """An inventory that uses a relative symlink to pull in an external
        class directory must continue to work when wildcard expansion
        materializes a temporary copy.
        """
        with tempfile.TemporaryDirectory() as tmp:
            external = os.path.join(tmp, "external_classes")
            os.makedirs(external)
            _write(
                os.path.join(external, "ext.yml"),
                {"parameters": {"from_external": True}},
            )

            inv = _build_inventory(
                tmp,
                {"common.yml": {}},
                ["common", "ext.*"],
            )
            # Relative symlink: inventory/classes/ext -> ../../external_classes
            symlink_path = os.path.join(inv, "classes", "ext")
            rel_target = os.path.relpath(external, os.path.join(inv, "classes"))
            os.symlink(rel_target, symlink_path)

            rendered = self._render(inv)
            self.assertIn("common", rendered)
            self.assertIn("ext.ext", rendered)


class ReclassWildcardIntegrationTest(_WildcardIntegrationMixin, unittest.TestCase):
    inventory_factory = staticmethod(
        lambda inv_path, ignore_missing=False: ReclassInventory(
            inventory_path=inv_path,
            ignore_class_not_found=ignore_missing,
            enable_class_wildcards=True,
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
            inv = ReclassInventory(inventory_path=inv_path, enable_class_wildcards=True)
            self.assertEqual(inv.original_inventory_path, inv_path)
            # Materialization happened -- backend path differs from original.
            self.assertNotEqual(inv.inventory_path, inv_path)

    def test_no_wildcards_means_no_materialization(self):
        """When no wildcard entries exist, ``inventory_path`` must remain
        the original path even when wildcards are enabled.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {}},
                ["common"],
            )
            inv = ReclassInventory(inventory_path=inv_path, enable_class_wildcards=True)
            self.assertEqual(inv.inventory_path, inv_path)
            self.assertEqual(inv.original_inventory_path, inv_path)

    def test_ignore_class_notfound_regexp_interaction(self):
        """Wildcard expansion happens before reclass's regex check.  A regex
        in ``reclass-config.yml`` that would have matched the pattern string
        can no longer intercept it because the expander raises first.
        """
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = _build_inventory(
                tmp,
                {"common.yml": {}},
                ["common", "pattern-*"],
            )
            # Write a reclass config that would skip 'pattern-*' if reclass
            # saw the raw pattern string.
            _write(
                os.path.join(inv_path, "reclass-config.yml"),
                {"ignore_class_notfound_regexp": "pattern-.*"},
            )
            # The expander sees 'pattern-*', finds no matches, and raises
            # because ignore_class_not_found defaults to False.  reclass's
            # regex never gets a chance to see the pattern.
            with self.assertRaises(InventoryError):
                ReclassInventory(
                    inventory_path=inv_path,
                    enable_class_wildcards=True,
                    ignore_class_not_found=False,
                )

            # With ignore_class_not_found=True, the unmatched pattern is
            # silently dropped and the inventory loads successfully.
            inv = ReclassInventory(
                inventory_path=inv_path,
                enable_class_wildcards=True,
                ignore_class_not_found=True,
            )
            rendered = list(inv.targets["example"].classes)
            self.assertIn("common", rendered)


@unittest.skipUnless(_backend_available("reclass_rs"), "reclass_rs not available")
class ReclassRsWildcardIntegrationTest(_WildcardIntegrationMixin, unittest.TestCase):
    inventory_factory = staticmethod(_make_reclass_rs_inventory)


@unittest.skipUnless(_backend_available("omegaconf"), "omegaconf not available")
class OmegaConfWildcardIntegrationTest(_WildcardIntegrationMixin, unittest.TestCase):
    inventory_factory = staticmethod(_make_omegaconf_inventory)


if __name__ == "__main__":
    unittest.main()
