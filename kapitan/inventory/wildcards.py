#!/usr/bin/env python3

# Copyright 2026 The Kapitan Authors
# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Wildcard expansion for inventory ``classes:`` lists.

Implements the feature requested in kapicorp/kapitan#1084: allow class
entries such as ``*``, ``clusters.*`` or ``dev-*`` to be expanded into the
matching set of concrete class names before the inventory backend resolves
inheritance.

Backend-agnostic strategy: when any target or class file contains wildcard
entries in its ``classes:`` list, we materialize a temporary copy of the
inventory tree with those entries pre-expanded. The chosen inventory backend
(reclass, reclass-rs, omegaconf) is then pointed at the materialized path
and never has to know about wildcards.
"""

from __future__ import annotations

import atexit
import fnmatch
import logging
import os
import shutil
import tempfile
from typing import Iterable

import yaml

from kapitan.errors import InventoryError


logger = logging.getLogger(__name__)


GLOB_METACHARACTERS = frozenset("*?[")
YAML_EXTENSIONS = (".yml", ".yaml")


def is_pattern(name: str) -> bool:
    """Return True if ``name`` contains any glob metacharacter."""
    return isinstance(name, str) and any(c in GLOB_METACHARACTERS for c in name)


def _looks_like_reclass_reference(entry: str) -> bool:
    """Return True if ``entry`` looks like a Reclass / Kapitan parameter
    reference such as ``${some_var}`` or ``${?optional_var}``.

    Such entries must never be treated as glob patterns: they are resolved
    by the inventory backend after class inheritance has been applied, and
    the wildcard expander has no way to resolve them.
    """
    if not isinstance(entry, str):
        return False
    return "${" in entry and "}" in entry


def discover_classes(classes_path: str) -> list[str]:
    """Return a sorted, deduplicated list of class names found under
    ``classes_path``.

    Class names are derived from the relative path of each YAML file:

    * ``classes/common.yml``        -> ``common``
    * ``classes/clusters/prod.yml`` -> ``clusters.prod``
    * ``classes/foo/init.yml``      -> ``foo`` (reclass ``init`` convention)
    * ``classes/init.yml``          -> ``init`` (root-level init is a real class)

    Hidden files/directories (names starting with ``.``) and non-YAML files
    are ignored.

    .. note:: ``followlinks=True`` is used so symlinked component directories
       (common in Commodore) are traversed.  Circular symlinks can cause
       infinite recursion; avoid them in ``inventory/classes/``.
    """
    found: set[str] = set()
    if not os.path.isdir(classes_path):
        return []

    for root, dirs, files in os.walk(classes_path, followlinks=True):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if filename.startswith("."):
                continue
            name, ext = os.path.splitext(filename)
            if ext not in YAML_EXTENSIONS:
                continue
            relpath = os.path.relpath(root, classes_path)
            parts: list[str] = [] if relpath in (".", "") else relpath.split(os.sep)
            if name == "init":
                # foo/init.yml -> "foo" (keep parent), but classes/init.yml -> "init"
                if not parts:
                    parts = ["init"]
            else:
                parts.append(name)
            found.add(".".join(parts))

    return sorted(found)


def _matches(pattern: str, available: Iterable[str]) -> list[str]:
    """Return sorted class names from ``available`` that match ``pattern``.

    Patterns are always matched against the **full dotted class name** using
    :func:`fnmatch.fnmatchcase`.  No special-case is made for patterns that
    do or do not contain ``.``: ``dev-*`` matches only top-level class names
    starting with ``dev-``, and ``*.dev-*`` is required to match
    ``apps.dev-api`` and similar nested classes.  Keeping the rule boring
    avoids surprises and makes the documentation simple.
    """
    return sorted(c for c in available if fnmatch.fnmatchcase(c, pattern))


def _add_if_new(entry: str, seen: set[str], out: list[str]) -> bool:
    """Append ``entry`` to ``out`` if it has not been seen before.

    Returns ``True`` if the entry was added, ``False`` if it was a duplicate.
    """
    if entry in seen:
        return False
    seen.add(entry)
    out.append(entry)
    return True


def expand_class_patterns(
    class_entries: list,
    available_classes: Iterable[str],
    ignore_class_not_found: bool = False,
) -> list[str]:
    """Expand wildcard ``class_entries`` against ``available_classes``.

    * Exact (non-pattern) entries are kept in their original position and
      passed through unchanged so the underlying inventory backend can
      apply its own missing-class handling.
    * Entries that exactly match an existing class name are treated as
      literal includes even if they contain glob metacharacters (e.g.
      ``config[html]``).  This preserves backward compatibility for
      inventories that have literal metacharacters in class names.
    * Entries that look like Reclass / Kapitan parameter references
      (``${var}``, ``${?var}``) are passed through unchanged even if they
      contain a glob metacharacter, because they must be resolved by the
      backend after class inheritance.
    * Wildcard entries are replaced in-place by their lexicographically
      sorted set of matches.
    * Duplicates (across exact and expanded entries) are removed,
      preserving the first occurrence.  This matches reclass behavior;
      other backends may already deduplicate too.
    * An unmatched pattern raises :class:`InventoryError` unless
      ``ignore_class_not_found`` is set.
    """
    available_list = list(available_classes)
    available_set = set(available_list)
    seen: set[str] = set()
    out: list[str] = []

    for entry in class_entries:
        # Defensive: skip non-string entries.  Malformed YAML or backend
        # preprocessing can produce integers, None, or booleans in classes:.
        if not isinstance(entry, str):
            continue

        # Reclass references are always preserved verbatim.
        if _looks_like_reclass_reference(entry):
            _add_if_new(entry, seen, out)
            continue

        # Exact match takes precedence over pattern expansion.  If a class
        # with this exact name exists, treat it as a literal include even
        # when the name contains glob metacharacters (e.g. "config[html]").
        if entry in available_set:
            _add_if_new(entry, seen, out)
            continue

        # Non-pattern entries that don't match an existing class are passed
        # through unchanged so the backend can apply its own missing-class
        # handling.
        if not is_pattern(entry):
            _add_if_new(entry, seen, out)
            continue

        matches = _matches(entry, available_list)
        if not matches and not ignore_class_not_found:
            raise InventoryError(
                f"Class pattern '{entry}' did not match any classes in inventory."
            )
        for match in matches:
            _add_if_new(match, seen, out)

    return out


# ---------------------------------------------------------------------------
# Backend-agnostic pre-expansion: materialize an inventory tree with
# wildcard ``classes:`` entries already expanded.
# ---------------------------------------------------------------------------


def _safe_load_yaml(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return None


def _files_with_wildcards(inventory_path: str) -> list[str]:
    """Return list of YAML files under ``inventory_path/{targets,classes}``
    whose ``classes:`` list contains at least one wildcard entry.

    A cheap text-level pre-filter skips full YAML parsing for files that
    contain no glob metacharacter at all.  This is only a heuristic: many
    inventories contain ``*``, ``[`` or ``?`` in parameter values (e.g.
    AWS ARNs, secret references, YAML anchors) so the pre-filter can
    still have a high false-positive rate.  Correctness does not depend
    on the pre-filter; any file that survives it is parsed and validated.
    """
    out: list[str] = []
    for sub in ("targets", "classes"):
        base = os.path.join(inventory_path, sub)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base, followlinks=True):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if filename.startswith("."):
                    continue
                if not filename.endswith(YAML_EXTENSIONS):
                    continue
                path = os.path.join(root, filename)
                # Fast path: if the raw file contains no glob metacharacter
                # there cannot be a wildcard class entry to expand.
                try:
                    with open(path, encoding="utf-8") as fh:
                        text = fh.read()
                except OSError:
                    continue
                if not any(c in text for c in GLOB_METACHARACTERS):
                    continue
                data = _safe_load_yaml(text)
                if not isinstance(data, dict):
                    continue
                classes = data.get("classes")
                if not isinstance(classes, list):
                    continue
                if any(
                    is_pattern(c) and not _looks_like_reclass_reference(c)
                    for c in classes
                ):
                    out.append(path)
    return out


def _fix_relative_symlinks(src_root: str, dest_root: str):
    """After copying an inventory tree, rewrite relative symlinks that
    point outside the copied tree so they resolve correctly.

    ``shutil.copytree(..., symlinks=True)`` preserves symlink target paths
    verbatim.  A relative symlink such as ``ext -> ../../external_classes``
    that resolved from the original inventory will break in the temporary
    copy because the relative base has moved.  We walk the copied tree and
    convert any such broken relative symlink to an absolute path based on
    the original target's resolved absolute path.
    """
    for dirpath, dirs, filenames in os.walk(dest_root, followlinks=False):
        # Process both file and directory symlinks.
        for name in list(dirs) + filenames:
            dest_link = os.path.join(dirpath, name)
            if not os.path.islink(dest_link):
                continue
            target = os.readlink(dest_link)
            if os.path.isabs(target):
                continue
            # Does the relative target resolve from the new location?
            dest_resolved = os.path.normpath(
                os.path.join(dirpath, target)
            )
            if os.path.exists(dest_resolved):
                continue
            # Try to resolve from the corresponding original location.
            rel_dir = os.path.relpath(dirpath, dest_root)
            src_link = os.path.join(src_root, rel_dir, name)
            if not os.path.islink(src_link):
                continue
            src_target = os.readlink(src_link)
            if os.path.isabs(src_target):
                continue
            src_resolved = os.path.normpath(
                os.path.join(os.path.dirname(src_link), src_target)
            )
            if os.path.exists(src_resolved):
                # Rewrite to absolute so the materialized inventory works.
                os.remove(dest_link)
                os.symlink(src_resolved, dest_link)


def materialize_expanded_inventory(
    inventory_path: str,
    ignore_class_not_found: bool = False,
    enable_wildcards: bool = False,
) -> str:
    """If ``enable_wildcards`` is True and any target/class YAML under
    ``inventory_path`` contains wildcard class entries, return a path to a
    temporary copy of the inventory with those entries pre-expanded.
    Otherwise return ``inventory_path`` unchanged.

    ``enable_wildcards`` defaults to ``False`` so that inventories with
    literal glob metacharacters in class names (e.g. ``config[html]``) or
    Reclass references that contain ``?`` are never treated as patterns
    unless the caller has explicitly opted in.

    The temporary directory is registered for cleanup via :mod:`atexit`.
    """
    if not enable_wildcards:
        return inventory_path

    if not os.path.isdir(inventory_path):
        return inventory_path

    files_to_expand = _files_with_wildcards(inventory_path)
    if not files_to_expand:
        return inventory_path

    classes_path = os.path.join(inventory_path, "classes")
    available = discover_classes(classes_path)

    tmp_root = tempfile.mkdtemp(prefix="kapitan_inv_")
    atexit.register(shutil.rmtree, tmp_root, ignore_errors=True)

    base_name = os.path.basename(os.path.normpath(inventory_path)) or "inventory"
    dest = os.path.join(tmp_root, base_name)
    shutil.copytree(inventory_path, dest, symlinks=True)

    # Fix relative symlinks that now point outside the temp tree.
    _fix_relative_symlinks(inventory_path, dest)

    logger.debug(
        f"Materialized inventory with wildcard class expansion at {dest} "
        f"(rewrote {len(files_to_expand)} file(s))"
    )

    for src in files_to_expand:
        rel = os.path.relpath(src, inventory_path)
        out_path = os.path.join(dest, rel)
        data = _safe_load_yaml(out_path)
        if not isinstance(data, dict):
            continue
        original = data.get("classes") or []
        data["classes"] = expand_class_patterns(
            original, available, ignore_class_not_found=ignore_class_not_found
        )
        with open(out_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False)

    return dest
