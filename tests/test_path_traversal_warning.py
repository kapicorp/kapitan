# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Path-traversal warnings for file accessors.

These cover ``warn_on_path_traversal`` and the resource native callbacks that
use it. The guard is warn-only: it must log when a resolved path escapes its
search paths, and stay silent for ordinary in-tree access. It must never block.
"""

import logging

import pytest

from kapitan import resources
from kapitan.utils import warn_on_path_traversal


pytestmark = pytest.mark.unit


def _write(path, content=""):
    with open(path, "w") as f:
        f.write(content)


def test_warns_when_path_escapes_root(tmp_path, caplog):
    root = tmp_path / "inventory"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    _write(outside, "ssh-key")

    with caplog.at_level(logging.WARNING):
        warn_on_path_traversal([str(root)], str(root / ".." / "secret.txt"), "test")

    assert any("escapes its search path" in r.message for r in caplog.records)


def test_silent_for_path_within_root(tmp_path, caplog):
    root = tmp_path / "inventory"
    root.mkdir()
    inside = root / "values.yaml"
    _write(inside)

    with caplog.at_level(logging.WARNING):
        warn_on_path_traversal([str(root)], str(inside), "test")

    assert caplog.records == []


def test_silent_when_contained_in_any_root(tmp_path, caplog):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    inside_b = root_b / "f.yaml"
    _write(inside_b)

    with caplog.at_level(logging.WARNING):
        warn_on_path_traversal([str(root_a), str(root_b)], str(inside_b), "test")

    assert caplog.records == []


def test_read_file_warns_on_traversal_but_still_reads(tmp_path, caplog):
    search_dir = tmp_path / "lib"
    search_dir.mkdir()
    secret = tmp_path / "id_rsa"
    _write(secret, "PRIVATE KEY")

    with caplog.at_level(logging.WARNING):
        content = resources.read_file([str(search_dir)], "../id_rsa")

    # warn-only: the read still succeeds, but the escape is logged
    assert content == "PRIVATE KEY"
    assert any(
        "read_file" in r.message and "escapes its search path" in r.message
        for r in caplog.records
    )


def test_read_file_silent_for_in_tree_file(tmp_path, caplog):
    search_dir = tmp_path / "lib"
    search_dir.mkdir()
    _write(search_dir / "data.txt", "ok")

    with caplog.at_level(logging.WARNING):
        content = resources.read_file([str(search_dir)], "data.txt")

    assert content == "ok"
    assert caplog.records == []
