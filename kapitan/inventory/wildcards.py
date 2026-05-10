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
    """
    found: set[str] = set()
    if not os.path.isdir(classes_path):
        return []

    for root, dirs, files in os.walk(classes_path):
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

    Patterns containing a ``.`` are matched against the full dotted class
    name. Patterns without ``.`` are matched against the basename segment
    (the part after the last ``.``), so ``dev-*`` matches both ``dev-common``
    and ``apps.dev-api`` as described in issue #1084.
    """
    if "." in pattern:
        return sorted(c for c in available if fnmatch.fnmatchcase(c, pattern))
    return sorted(
        c for c in available if fnmatch.fnmatchcase(c.rsplit(".", 1)[-1], pattern)
    )


def expand_class_patterns(
    class_entries: list[str],
    available_classes: Iterable[str],
    ignore_class_not_found: bool = False,
) -> list[str]:
    """Expand wildcard ``class_entries`` against ``available_classes``.

    * Exact (non-pattern) entries are kept in their original position and
      passed through unchanged so the underlying inventory backend can
      apply its own missing-class handling.
    * Wildcard entries are replaced in-place by their lexicographically
      sorted set of matches.
    * Duplicates (across exact and expanded entries) are removed,
      preserving the first occurrence.
    * An unmatched pattern raises :class:`InventoryError` unless
      ``ignore_class_not_found`` is set.
    """
    available_list = list(available_classes)
    seen: set[str] = set()
    out: list[str] = []

    for entry in class_entries:
        if not is_pattern(entry):
            if entry not in seen:
                seen.add(entry)
                out.append(entry)
            continue

        matches = _matches(entry, available_list)
        if not matches and not ignore_class_not_found:
            raise InventoryError(
                f"Class pattern '{entry}' did not match any classes in inventory."
            )
        for match in matches:
            if match not in seen:
                seen.add(match)
                out.append(match)

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

    Performance: a cheap text-level pre-check skips full YAML parsing for
    files that contain no glob metacharacter at all (the common case).
    """
    out: list[str] = []
    for sub in ("targets", "classes"):
        base = os.path.join(inventory_path, sub)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
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
                data = _safe_load_yaml(path)
                if not isinstance(data, dict):
                    continue
                classes = data.get("classes")
                if not isinstance(classes, list):
                    continue
                if any(is_pattern(c) for c in classes):
                    out.append(path)
    return out


def materialize_expanded_inventory(
    inventory_path: str, ignore_class_not_found: bool = False
) -> str:
    """If any target/class YAML under ``inventory_path`` contains wildcard
    class entries, return a path to a temporary copy of the inventory with
    those entries pre-expanded. Otherwise return ``inventory_path`` unchanged.

    The temporary directory is registered for cleanup via :mod:`atexit`.
    """
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
