# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Path-traversal handling for file accessors.

These cover ``check_path_traversal`` and the resource native callbacks that use
it. The reaction is configurable: ``warn`` logs and lets the read continue,
``error`` raises, and ``off`` disables the check. ``warn`` is the default and
must never block.
"""

import logging

import pytest

from kapitan import resources
from kapitan.errors import PathTraversalError
from kapitan.utils import check_path_traversal, set_path_traversal_mode


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_mode():
    # Each test starts from the default; restore it afterwards because the mode
    # is a process-wide global.
    set_path_traversal_mode("warn")
    yield
    set_path_traversal_mode("warn")


def _write(path, content=""):
    with open(path, "w") as f:
        f.write(content)


def test_warns_when_path_escapes_root(tmp_path, caplog):
    root = tmp_path / "inventory"
    root.mkdir()
    _write(tmp_path / "secret.txt", "ssh-key")

    with caplog.at_level(logging.WARNING):
        check_path_traversal([str(root)], str(root / ".." / "secret.txt"), "test")

    assert any("escapes its search" in r.message for r in caplog.records)


def test_silent_for_path_within_root(tmp_path, caplog):
    root = tmp_path / "inventory"
    root.mkdir()
    inside = root / "values.yaml"
    _write(inside)

    with caplog.at_level(logging.WARNING):
        check_path_traversal([str(root)], str(inside), "test")

    assert caplog.records == []


def test_silent_when_contained_in_any_root(tmp_path, caplog):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    inside_b = root_b / "f.yaml"
    _write(inside_b)

    with caplog.at_level(logging.WARNING):
        check_path_traversal([str(root_a), str(root_b)], str(inside_b), "test")

    assert caplog.records == []


def test_error_mode_raises_on_escape(tmp_path):
    root = tmp_path / "inventory"
    root.mkdir()
    set_path_traversal_mode("error")

    with pytest.raises(PathTraversalError):
        check_path_traversal([str(root)], str(root / ".." / "secret.txt"), "test")


def test_off_mode_is_silent_and_never_raises(tmp_path, caplog):
    root = tmp_path / "inventory"
    root.mkdir()
    set_path_traversal_mode("off")

    with caplog.at_level(logging.WARNING):
        check_path_traversal([str(root)], str(root / ".." / "secret.txt"), "test")

    assert caplog.records == []


def test_invalid_mode_rejected():
    with pytest.raises(ValueError, match="invalid path traversal mode"):
        set_path_traversal_mode("loud")


def test_read_file_warns_on_traversal_but_still_reads(tmp_path, caplog):
    search_dir = tmp_path / "lib"
    search_dir.mkdir()
    _write(tmp_path / "id_rsa", "PRIVATE KEY")

    with caplog.at_level(logging.WARNING):
        content = resources.read_file([str(search_dir)], "../id_rsa")

    # warn-only: the read still succeeds, but the escape is logged
    assert content == "PRIVATE KEY"
    assert any(
        "read_file" in r.message and "escapes its search" in r.message
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


def test_search_imports_warns_when_import_escapes_search_paths(tmp_path, caplog):
    # Drives the multi-root path (cwd + install path + search paths) end to end:
    # an import that climbs out of both cwd and the search path must warn.
    inventory = tmp_path / "inv"
    cwd = inventory / "components"
    cwd.mkdir(parents=True)
    _write(tmp_path / "outside.libsonnet", "{}")

    with caplog.at_level(logging.WARNING):
        resolved, content = resources.search_imports(
            str(cwd), "../../outside.libsonnet", [str(inventory)]
        )

    assert content == b"{}"
    assert any(
        "jsonnet import" in r.message and "escapes its search" in r.message
        for r in caplog.records
    )
