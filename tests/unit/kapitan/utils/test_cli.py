# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest
import yaml

import kapitan.utils.cli as utils_cli
from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.inventory import InventoryBackends


@pytest.mark.parametrize(
    ("dot_kapitan_version", "current_version", "expected"),
    [
        ("0.22.0", "0.22.0", "equal"),
        ("0.22.0-rc.1", "0.22.0-rc.1", "equal"),
        ("0.22", "0.22.1", "equal"),
        ("0.22", "0.22.1-rc.1", "equal"),
        ("0.22.1", "0.22.0", "greater"),
        ("0.22.0", "0.22.0-rc.1", "greater"),
        ("0.22.1-rc.1", "0.22.0-rc.1", "greater"),
        ("0.23.0-rc.1", "0.22.0-rc.1", "greater"),
        ("0.22.0", "0.22.1", "lower"),
        ("0.22.0-rc.1", "0.22.0", "lower"),
        ("0.22.0-rc.1", "0.22.1-rc.1", "lower"),
        ("0.22.0-rc.1", "0.23.0-rc.1", "lower"),
    ],
)
def test_compare_versions(dot_kapitan_version, current_version, expected):
    assert utils_cli.compare_versions(dot_kapitan_version, current_version) == expected


def _write_dot_kapitan(base_path: Path, config):
    dot_path = base_path / ".kapitan"
    dot_path.write_text(yaml.safe_dump(config), encoding="utf-8")


@pytest.fixture
def in_temp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    reset_cache()


def test_from_dot_kapitan_returns_fallback_when_file_is_missing(in_temp_dir):
    assert (
        utils_cli.from_dot_kapitan("compile", "inventory-path", "./some/fallback")
        == "./some/fallback"
    )


def test_from_dot_kapitan_returns_fallback_when_option_is_missing(in_temp_dir):
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        utils_cli.from_dot_kapitan("inventory", "inventory-path", "./some/fallback")
        == "./some/fallback"
    )


def test_from_dot_kapitan_prefers_command_specific_option(in_temp_dir):
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        utils_cli.from_dot_kapitan("compile", "inventory-path", "./some/fallback")
        == "./path/to/inv"
    )


def test_global_option(in_temp_dir):
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-path": "./some/path"},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        utils_cli.from_dot_kapitan("inventory", "inventory-path", "./some/fallback")
        == "./some/path"
    )


def test_command_over_global_option(in_temp_dir):
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-path": "./some/path"},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        utils_cli.from_dot_kapitan("compile", "inventory-path", "./some/fallback")
        == "./path/to/inv"
    )


def test_compare_versions_and_check_version(monkeypatch, tmp_path, capsys):
    assert utils_cli.compare_versions("1.2.3", "1.2.3") == "equal"
    assert utils_cli.compare_versions("1.2.4", "1.2.3") == "greater"
    assert utils_cli.compare_versions("1.2.3", "1.2.4") == "lower"
    assert utils_cli.compare_versions("1.2.3-rc1", "1.2.3") == "greater"

    kapitan_config = tmp_path / ".kapitan"
    kapitan_config.write_text("version: 1.0.0\n", encoding="utf-8")
    cached.dot_kapitan = None
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(utils_cli, "VERSION", "2.0.0")

    with pytest.raises(SystemExit) as excinfo:
        utils_cli.check_version()

    assert excinfo.value.code == 1
    assert "Current version" in capsys.readouterr().out
    cached.dot_kapitan = None


def test_dictionary_hash_and_dot_kapitan_cached_short_circuit(monkeypatch):
    cached.dot_kapitan = {"cached": True}

    def _should_not_be_called(_path):
        raise AssertionError("filesystem check should be skipped when cache is set")

    monkeypatch.setattr(utils_cli.os.path, "exists", _should_not_be_called)
    assert utils_cli.dot_kapitan_config() == {"cached": True}
    cached.dot_kapitan = None


def test_check_version_equal_greater_and_missing_version(monkeypatch, capsys):
    monkeypatch.setattr(utils_cli, "dot_kapitan_config", lambda: {"version": "1.2.3"})
    monkeypatch.setattr(utils_cli, "VERSION", "1.2.3")
    assert utils_cli.check_version() is None

    monkeypatch.setattr(utils_cli, "dot_kapitan_config", lambda: {"version": "2.0.0"})
    monkeypatch.setattr(utils_cli, "VERSION", "1.0.0")
    with pytest.raises(SystemExit) as excinfo:
        utils_cli.check_version()
    assert excinfo.value.code == 1
    assert "Upgrade kapitan to '2.0.0'" in capsys.readouterr().out

    monkeypatch.setattr(utils_cli, "dot_kapitan_config", dict)
    assert utils_cli.check_version() is None


def test_compare_versions_covers_non_orderable_part_fallthrough():
    class _VersionPart:
        def __eq__(self, _other):
            return False

        def __gt__(self, _other):
            return False

        def __lt__(self, _other):
            return False

    class _VersionLike:
        @staticmethod
        def replace(_old, _new):
            return _VersionLike()

        @staticmethod
        def split(_sep):
            return [_VersionPart()]

    assert utils_cli.compare_versions(_VersionLike(), _VersionLike()) == "equal"


def test_check_version_covers_unexpected_compare_result_branch(monkeypatch):
    monkeypatch.setattr(utils_cli, "dot_kapitan_config", lambda: {"version": "1.2.3"})
    monkeypatch.setattr(utils_cli, "compare_versions", lambda *_args: "unexpected")

    with pytest.raises(SystemExit) as excinfo:
        utils_cli.check_version()
    assert excinfo.value.code == 1


def test_check_version_ignores_missing_version_key(monkeypatch):
    monkeypatch.setattr(
        utils_cli, "dot_kapitan_config", lambda: {"not_version": "1.0.0"}
    )
    assert utils_cli.check_version() is None
