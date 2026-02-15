# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import contextlib
import os
from unittest.mock import patch

import pytest

from kapitan.cli import build_parser
from kapitan.cli import main as kapitan
from kapitan.refs.secrets.vaultkv import VaultSecret
from tests.support.helpers import write_text_file


@contextlib.contextmanager
def set_env(**environ):
    old_environ = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


def _assert_write_reveal_file(
    refs_cli,
    tmp_path,
    refs_path,
    *,
    token,
    secret_content,
    tag_content,
    expected_output,
    base64_encoded=False,
    key=None,
    recipients=None,
):
    secret_file = write_text_file(tmp_path / "secret.txt", secret_content)
    refs_cli.write(
        token,
        secret_file,
        refs_path,
        base64=base64_encoded,
        key=key,
        recipients=recipients,
    )
    test_tag_file = write_text_file(tmp_path / "tag.txt", tag_content)
    stdout = refs_cli.reveal_file(test_tag_file, refs_path)
    assert stdout == expected_output


def test_cli_secret_reveal_tag(
    refs_cli, refs_path, tmp_path, kapitan_stdout, setup_gpg_key, gnupg_home, gpg_env
):
    test_secret_content = "I am another secret!"
    test_secret_file = write_text_file(tmp_path / "secret.txt", test_secret_content)

    refs_cli.write(
        "gpg:test_secret",
        test_secret_file,
        refs_path,
        recipients=["example@kapitan.dev"],
    )

    test_tag_content = "?{gpg:test_secret}"
    stdout = kapitan_stdout(
        "refs", "--reveal", "--tag", test_tag_content, "--refs-path", refs_path
    )
    assert stdout == test_secret_content


def test_cli_secret_reveal_b64_tag(
    refs_cli, refs_path, tmp_path, kapitan_stdout, setup_gpg_key, gnupg_home, gpg_env
):
    test_secret_content = "I am another secret!"
    test_secret_file = write_text_file(tmp_path / "secret.txt", test_secret_content)

    refs_cli.write(
        "gpg:test_secretb64",
        test_secret_file,
        refs_path,
        base64=True,
        recipients=["example@kapitan.dev"],
    )

    stdout_base64 = base64.b64decode(
        kapitan_stdout(
            "refs",
            "--reveal",
            "--tag",
            "?{gpg:test_secretb64}",
            "--refs-path",
            refs_path,
        )
    ).decode()
    assert stdout_base64 == test_secret_content


def test_cli_secret_write_reveal_gpg(
    refs_cli, refs_path, tmp_path, setup_gpg_key, gnupg_home, gpg_env
):
    _assert_write_reveal_file(
        refs_cli,
        tmp_path,
        refs_path,
        token="gpg:test_secret",
        secret_content="I am a secret!",
        tag_content="revealing: ?{gpg:test_secret}",
        expected_output="revealing: I am a secret!",
        recipients=["example@kapitan.dev"],
    )


def test_cli_secret_base64_write_reveal_gpg(
    refs_cli, refs_path, tmp_path, setup_gpg_key, gnupg_home, gpg_env
):
    secret_content = "I am another secret!"
    _assert_write_reveal_file(
        refs_cli,
        tmp_path,
        refs_path,
        token="gpg:test_secretb64",
        secret_content=secret_content,
        tag_content="?{gpg:test_secretb64}",
        expected_output=base64.b64encode(secret_content.encode()).decode(),
        base64_encoded=True,
        recipients=["example@kapitan.dev"],
    )


def test_cli_ref_reveal_recursive_dir(refs_path, tmp_path, kapitan_stdout):
    for ref_count in range(1, 4):
        ref_content = f"I am ref{ref_count}!"
        ref_file = write_text_file(tmp_path / f"ref{ref_count}.txt", ref_content)

        kapitan(
            "refs",
            "--write",
            f"base64:test_ref_{ref_count}",
            "-f",
            str(ref_file),
            "--refs-path",
            refs_path,
        )

    unrevealed_dir = tmp_path / "unrevealed"
    ref_content = "---\nref_value_{}: {}\n"

    some_dir = unrevealed_dir / "some" / "dir"
    some_dir_other = unrevealed_dir / "some" / "dir" / "another"
    some_dir_another = unrevealed_dir / "some" / "dir" / "another" / "dir"
    some_dir_another.mkdir(parents=True)
    some_dir.mkdir(parents=True, exist_ok=True)
    some_dir_other.mkdir(parents=True, exist_ok=True)

    expected_output = ""
    for count, path in enumerate((some_dir, some_dir_other, some_dir_another), 1):
        manifest_path = path / f"{count}.yml"
        ref = f"?{{base64:test_ref_{count}}}"
        manifest_path.write_text(ref_content.format(count, ref))

        expected_ref_rev = f"I am ref{count}!"
        expected_output += ref_content.format(count, expected_ref_rev)

    stdout = kapitan_stdout(
        "refs", "--reveal", "-f", str(some_dir), "--refs-path", refs_path
    )
    assert stdout == expected_output


def test_cli_secret_validate_targets():
    with pytest.raises(SystemExit) as excinfo:
        kapitan(
            "refs",
            "--validate-targets",
            "--refs-path",
            "examples/kubernetes/refs/targets/",
            "--inventory-path",
            "examples/kubernetes/inventory/",
        )
    assert excinfo.value.code == 0


@pytest.mark.parametrize(
    ("token", "secret_content", "tag_content", "key"),
    [
        ("gkms:test_secret", "mock", "revealing: ?{gkms:test_secret}", "mock"),
        ("awskms:test_secret", "mock", "revealing: ?{awskms:test_secret}", "mock"),
        ("plain:test_secret", "secret_value!", "revealing: ?{plain:test_secret}", None),
        (
            "base64:test_secret",
            "secret_value!",
            "revealing: ?{base64:test_secret}",
            None,
        ),
    ],
)
def test_cli_secret_write_reveal_variants(
    refs_cli, refs_path, tmp_path, token, secret_content, tag_content, key
):
    _assert_write_reveal_file(
        refs_cli,
        tmp_path,
        refs_path,
        token=token,
        secret_content=secret_content,
        tag_content=tag_content,
        expected_output=f"revealing: {secret_content}",
        key=key,
    )


def test_cli_secret_ref_reveal_plain_ref(refs_cli, refs_path, tmp_path):
    test_secret_content = "secret_value!"
    test_secret_file = write_text_file(tmp_path / "secret.txt", test_secret_content)

    refs_cli.write("plain:test_secret", test_secret_file, refs_path)
    stdout = refs_cli.reveal_ref_file(f"{refs_path}/test_secret", refs_path)
    assert stdout == test_secret_content


def test_cli_secret_write_base64_encoded_ref(refs_cli, refs_path, tmp_path):
    test_secret_content = "secret_value!"
    test_secret_content_b64 = base64.b64encode(test_secret_content.encode())
    _assert_write_reveal_file(
        refs_cli,
        tmp_path,
        refs_path,
        token="base64:test_secret",
        secret_content=test_secret_content,
        tag_content="revealing: ?{base64:test_secret}",
        expected_output=f"revealing: {test_secret_content_b64.decode()}",
        base64_encoded=True,
    )


def _assert_subvar_reveal(reftype, refs_cli, refs_path, tmp_path):
    test_secret_content = """
var1:
  var2: hello
var3:
  var4: world
"""
    test_secret_file = write_text_file(tmp_path / "secret.yaml", test_secret_content)

    refs_cli.write(f"{reftype}:test_secret_subvar", test_secret_file, refs_path)

    test_tag_content = f"""
revealing1: ?{{{reftype}:test_secret_subvar@var1.var2}}
revealing2: ?{{{reftype}:test_secret_subvar@var3.var4}}
"""
    test_tag_file = write_text_file(tmp_path / "tags.txt", test_tag_content)
    stdout = refs_cli.reveal_file(test_tag_file, refs_path)
    expected = """
revealing1: {}
revealing2: {}
"""
    assert stdout == expected.format("hello", "world")


def test_cli_secret_subvar_ref(refs_cli, refs_path, tmp_path):
    _assert_subvar_reveal("plain", refs_cli, refs_path, tmp_path)
    _assert_subvar_reveal("base64", refs_cli, refs_path, tmp_path)


def test_cli_secret_subvar_gpg(
    refs_cli, refs_path, tmp_path, setup_gpg_key, gnupg_home, gpg_env
):
    test_secret_content = """
var1:
  var2: hello
var3:
  var4: world
"""
    test_secret_file = write_text_file(tmp_path / "secret.yaml", test_secret_content)

    refs_cli.write(
        "gpg:test_secret_subvar",
        test_secret_file,
        refs_path,
        recipients=["example@kapitan.dev"],
    )

    test_tag_content = """
revealing1: ?{gpg:test_secret_subvar@var1.var2}
revealing2: ?{gpg:test_secret_subvar@var3.var4}
"""
    test_tag_file = write_text_file(tmp_path / "tags.txt", test_tag_content)
    stdout = refs_cli.reveal_file(test_tag_file, refs_path)
    expected = """
revealing1: {}
revealing2: {}
"""
    assert stdout == expected.format("hello", "world")


def test_cli_secret_ref_reveal_gpg_ref(
    refs_cli, refs_path, tmp_path, setup_gpg_key, gnupg_home, gpg_env
):
    test_secret_content = "secret_value!"
    test_secret_file = write_text_file(tmp_path / "secret.txt", test_secret_content)

    refs_cli.write(
        "gpg:test_secret",
        test_secret_file,
        refs_path,
        recipients=["example@kapitan.dev"],
    )

    stdout = refs_cli.reveal_ref_file(f"{refs_path}/test_secret", refs_path)
    assert stdout == test_secret_content


@patch.object(VaultSecret, "_decrypt")
@pytest.mark.requires_vault
def test_cli_secret_write_vault(
    mock_reveal, refs_cli, vault_server, refs_path, tmp_path
):
    test_secret_content = "secret_value"
    test_secret_file = write_text_file(tmp_path / "secret.txt", test_secret_content)

    argv = [
        "refs",
        "--write",
        "vaultkv:test_secret",
        "-f",
        str(test_secret_file),
        "--refs-path",
        refs_path,
        "--vault-auth",
        "token",
        "--vault-mount",
        "secret",
        "--vault-path",
        "testpath",
        "--vault-key",
        "testkey",
    ]
    with set_env(VAULT_ADDR=vault_server.vault_url):
        kapitan(*argv)

    test_tag_file = write_text_file(
        tmp_path / "tag.txt", "revealing: ?{vaultkv:test_secret}"
    )

    mock_reveal.return_value = test_secret_content
    stdout = refs_cli.reveal_file(test_tag_file, refs_path)
    assert stdout == f"revealing: {test_secret_content}"


def test_cli_searchvar(kapitan_stdout):
    argv = [
        "searchvar",
        "mysql.replicas",
        "--inventory-path",
        "examples/kubernetes/inventory/",
    ]

    stdout = kapitan_stdout(*argv)
    assert stdout == "examples/kubernetes/inventory/targets/minikube-mysql.yml   1\n"


def test_cli_inventory(kapitan_stdout):
    argv = [
        "inventory",
        "-t",
        "minikube-es",
        "-F",
        "-p",
        "cluster",
        "--inventory-path",
        "examples/kubernetes/inventory/",
    ]

    stdout = kapitan_stdout(*argv)
    assert stdout == "id: minikube\nname: minikube\ntype: minikube\nuser: minikube\n"


def test_parser_aliases():
    parser = build_parser()
    aliases = {"c": "compile", "i": "inventory"}

    for alias, command in aliases.items():
        result = parser.parse_args([alias])
        assert result.name == command


def test_main_rejects_pattern_without_target_name():
    with pytest.raises(SystemExit):
        kapitan("inventory", "--pattern", "parameters.foo")
