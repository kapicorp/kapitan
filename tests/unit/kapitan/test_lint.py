# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
from types import SimpleNamespace

import pytest

from kapitan.errors import KapitanError
from kapitan.lint import (
    lint_orphan_secrets,
    lint_unused_classes,
    lint_yamllint,
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


def test_lint_unused_classes_handles_missing_dir_and_init_alias(tmp_path):
    inventory_path = tmp_path / "inventory"
    inventory_path.mkdir()

    with pytest.raises(KapitanError):
        lint_unused_classes(str(inventory_path))

    classes_dir = inventory_path / "classes" / "app"
    classes_dir.mkdir(parents=True)
    (classes_dir / "init.yml").write_text("parameters: {}\n", encoding="utf-8")
    targets_dir = inventory_path / "targets"
    targets_dir.mkdir()
    (targets_dir / "target.yml").write_text("classes:\n  - app\n", encoding="utf-8")

    assert lint_unused_classes(str(inventory_path)) == 0


def test_lint_orphan_secrets_reports_orphans(tmp_path):
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    (compiled_dir / "manifest.yaml").write_text("apiVersion: v1\n", encoding="utf-8")

    refs_dir = tmp_path / "refs" / "target"
    refs_dir.mkdir(parents=True)
    (refs_dir / "secret.yaml").write_text("type: base64\n", encoding="utf-8")

    assert lint_orphan_secrets(str(compiled_dir), str(tmp_path / "refs")) == 1


def test_lint_yamllint_uses_dotfile_and_handles_oserror(monkeypatch, tmp_path):
    inventory_path = tmp_path / "inventory"
    inventory_path.mkdir()
    (inventory_path / "values.yaml").write_text("key: value\n", encoding="utf-8")
    (tmp_path / ".yamllint").write_text(
        "rules: {line-length: disable}\n", encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kapitan.lint.linter.run", lambda *_args, **_kwargs: [])
    assert lint_yamllint(str(inventory_path)) == 0

    monkeypatch.setattr(
        "kapitan.lint.linter.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("boom")),
    )
    with pytest.raises(SystemExit) as excinfo:
        lint_yamllint(str(inventory_path))
    assert excinfo.value.code == -1


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


def test_start_lint_skip_combinations_cover_individual_checks(monkeypatch, tmp_path):
    inventory_path = tmp_path / "inventory"
    inventory_path.mkdir()

    monkeypatch.setattr("kapitan.lint.lint_yamllint", lambda _path: 2)
    monkeypatch.setattr("kapitan.lint.lint_unused_classes", lambda _path: 3)

    class_only_args = SimpleNamespace(
        fail_on_warning=False,
        skip_class_checks=False,
        skip_yamllint=True,
        inventory_path=str(inventory_path),
        search_secrets=False,
        refs_path="refs",
        compiled_path="compiled",
    )
    assert start_lint(class_only_args) == 3

    yaml_only_args = SimpleNamespace(
        fail_on_warning=False,
        skip_class_checks=True,
        skip_yamllint=False,
        inventory_path=str(inventory_path),
        search_secrets=False,
        refs_path="refs",
        compiled_path="compiled",
    )
    assert start_lint(yaml_only_args) == 2


def test_lint_orphan_secrets_returns_zero_when_all_secrets_are_used(tmp_path):
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    (compiled_dir / "manifest.yaml").write_text(
        "token: ?{base64:target/secret.yaml}\n", encoding="utf-8"
    )

    refs_dir = tmp_path / "refs" / "target"
    refs_dir.mkdir(parents=True)
    (refs_dir / "secret.yaml").write_text("type: base64\n", encoding="utf-8")

    assert lint_orphan_secrets(str(compiled_dir), str(tmp_path / "refs")) == 0
