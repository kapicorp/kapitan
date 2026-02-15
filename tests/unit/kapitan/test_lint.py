# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
from types import SimpleNamespace

import pytest

from kapitan.lint import (
    start_lint,
)


logging.basicConfig(level=logging.CRITICAL, format="%(message)s")


def test_start_lint_reports_expected_issue_count(isolated_test_resources):
    args = SimpleNamespace(
        fail_on_warning=False,
        skip_class_checks=False,
        skip_yamllint=False,
        inventory_path=f"{isolated_test_resources}/inventory",
        search_secrets=True,
        refs_path=f"{isolated_test_resources}/secrets",
        compiled_path=f"{isolated_test_resources}/compiled",
    )

    num_issues_found = start_lint(args)
    assert num_issues_found == 3


def test_start_lint_exits_when_no_checks_enabled():
    args = SimpleNamespace(
        fail_on_warning=False,
        skip_class_checks=True,
        skip_yamllint=True,
        inventory_path="inventory",
        search_secrets=False,
        refs_path="refs",
        compiled_path="compiled",
    )

    with pytest.raises(SystemExit) as excinfo:
        start_lint(args)
    assert excinfo.value.code == 1


def test_start_lint_fail_on_warning_exits(monkeypatch, tmp_path):
    inventory_path = tmp_path / "inventory"
    inventory_path.mkdir()

    monkeypatch.setattr("kapitan.lint.lint_yamllint", lambda _path: 1)
    monkeypatch.setattr("kapitan.lint.lint_unused_classes", lambda _path: 0)
    args = SimpleNamespace(
        fail_on_warning=True,
        skip_class_checks=False,
        skip_yamllint=False,
        inventory_path=str(inventory_path),
        search_secrets=False,
        refs_path="refs",
        compiled_path="compiled",
    )

    with pytest.raises(SystemExit) as excinfo:
        start_lint(args)
    assert excinfo.value.code == 1


def test_start_lint_invalid_inventory_path_still_returns_checks(monkeypatch):
    monkeypatch.setattr("kapitan.lint.os.path.isdir", lambda _path: False)
    args = SimpleNamespace(
        fail_on_warning=False,
        skip_class_checks=False,
        skip_yamllint=False,
        inventory_path="/tmp/missing-inventory",
        search_secrets=False,
        refs_path="refs",
        compiled_path="compiled",
    )

    assert start_lint(args) == 0
