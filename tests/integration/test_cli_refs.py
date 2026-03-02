# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from tests.support.helpers import run_kapitan_in_project


def test_refs_cli_base64_write_and_reveal_file(refs_cli, refs_path, tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("super secret value", encoding="utf-8")

    refs_cli.write("base64:test_secret", secret_file, refs_path)

    tag_file = tmp_path / "manifest.yml"
    tag_file.write_text("revealing: ?{base64:test_secret}\n", encoding="utf-8")

    stdout = refs_cli.reveal_file(tag_file, refs_path)
    assert "super secret value" in stdout


def test_refs_cli_plain_ref_reveal_from_ref_file(refs_cli, refs_path, tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("plain secret value", encoding="utf-8")

    refs_cli.write("plain:test_secret", secret_file, refs_path)

    stdout = refs_cli.reveal_ref_file(Path(refs_path) / "test_secret", refs_path)
    assert "plain secret value" in stdout


def test_refs_cli_base64_subvar_reveal(refs_cli, refs_path, tmp_path):
    secret_file = tmp_path / "secret.yml"
    secret_file.write_text(
        "var1:\n  var2: nested secret value\nvar3:\n  var4: another value\n",
        encoding="utf-8",
    )

    refs_cli.write("base64:test_secret_subvar", secret_file, refs_path)

    tag_file = tmp_path / "manifest.yml"
    tag_file.write_text(
        "revealing: ?{base64:test_secret_subvar@var1.var2}\n", encoding="utf-8"
    )

    stdout = refs_cli.reveal_file(tag_file, refs_path)
    assert "nested secret value" in stdout


@pytest.mark.usefixtures("setup_gpg_key")
def test_refs_cli_gpg_write_and_reveal_file(
    refs_cli, refs_path, tmp_path, gnupg_home, gpg_env
):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("gpg secret value", encoding="utf-8")

    refs_cli.write(
        "gpg:test_secret",
        secret_file,
        refs_path,
        recipients=["example@kapitan.dev"],
    )

    tag_file = tmp_path / "manifest.yml"
    tag_file.write_text("revealing: ?{gpg:test_secret}\n", encoding="utf-8")

    stdout = refs_cli.reveal_file(tag_file, refs_path)
    assert "gpg secret value" in stdout


def test_lint_cli_fails_on_real_fixture_warnings(isolated_test_resources):
    with pytest.raises(SystemExit) as excinfo:
        run_kapitan_in_project(
            isolated_test_resources,
            [
                "lint",
                "--fail-on-warning",
                "--search-secrets",
                "--inventory-path",
                "inventory",
                "--refs-path",
                "refs",
                "--compiled-path",
                "compiled",
            ],
        )

    assert excinfo.value.code == 1
