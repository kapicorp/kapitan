# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from argparse import Namespace

import pytest


@pytest.fixture
def cmd_parser_args():
    """Factory for kapitan.refs.cmd_parser CLI-style args."""
    defaults = {
        "refs_path": "refs",
        "write": None,
        "file": None,
        "binary": False,
        "base64": False,
        "target_name": None,
        "inventory_path": None,
        "recipients": [],
        "key": None,
        "vault_auth": None,
        "vault_mount": None,
        "vault_path": None,
        "vault_key": None,
        "ref_file": None,
        "tag": None,
        "update": None,
        "reveal": False,
        "update_targets": False,
        "validate_targets": False,
    }

    def _make(**overrides):
        args = defaults.copy()
        args.update(overrides)
        if "recipients" not in overrides:
            args["recipients"] = []
        return Namespace(**args)

    return _make


@pytest.fixture
def cmd_parser_secret_file(tmp_path):
    """Factory for cmd_parser input files under a test tmp_path."""

    def _create(name="secret.txt", content="data", binary=False):
        file_path = tmp_path / name
        if binary:
            payload = (
                content
                if isinstance(content, bytes | bytearray)
                else str(content).encode("utf-8")
            )
            file_path.write_bytes(payload)
        else:
            text = (
                content.decode("utf-8")
                if isinstance(content, bytes | bytearray)
                else str(content)
            )
            file_path.write_text(text, encoding="utf-8")
        return file_path

    return _create


@pytest.fixture
def cmd_parser_inventory():
    """Factory for lightweight inventory objects used by cmd_parser tests."""

    def _create(secrets, target_name="target"):
        return Namespace(
            targets={target_name: object()},
            get_parameters=lambda _target: Namespace(
                kapitan=Namespace(secrets=secrets)
            ),
        )

    return _create


@pytest.fixture
def patch_cmd_parser_inventory(monkeypatch):
    """Patch cmd_parser inventory and target token path discovery."""

    def _patch(inventory, target_token_paths):
        monkeypatch.setattr(
            "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
        )
        monkeypatch.setattr(
            "kapitan.refs.cmd_parser.search_target_token_paths",
            lambda _path, _targets: target_token_paths,
        )

    return _patch
