# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
import io
from argparse import Namespace

import pytest


@pytest.fixture
def refs_path(tmp_path):
    """Create an isolated refs path for secret management tests."""
    refs_dir = tmp_path / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    return str(refs_dir)


@pytest.fixture
def ref_controller(refs_path):
    from kapitan.refs.base import RefController

    return RefController(refs_path)


@pytest.fixture
def revealer(ref_controller):
    from kapitan.refs.base import Revealer

    return Revealer(ref_controller)


@pytest.fixture
def ref_controller_embedded(refs_path):
    from kapitan.refs.base import RefController

    return RefController(refs_path, embed_refs=True)


@pytest.fixture
def revealer_embedded(ref_controller_embedded):
    from kapitan.refs.base import Revealer

    return Revealer(ref_controller_embedded)


@pytest.fixture
def kapitan_stdout():
    """Run kapitan CLI and capture stdout."""
    from kapitan.cli import main as kapitan

    def _run(*argv):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            kapitan(*argv)
        return stdout.getvalue()

    return _run


@pytest.fixture
def refs_cli(kapitan_stdout):
    """Helpers for common refs CLI write/reveal flows."""
    from kapitan.cli import main as kapitan

    def _write(
        token,
        file_path,
        refs_path,
        *,
        base64=False,
        key=None,
        recipients=None,
        extra_args=None,
    ):
        argv = [
            "refs",
            "--write",
            token,
            "-f",
            str(file_path),
            "--refs-path",
            refs_path,
        ]
        if base64:
            argv.append("--base64")
        if key:
            argv.extend(["--key", key])
        if recipients:
            for recipient in recipients:
                argv.extend(["--recipients", recipient])
        if extra_args:
            argv.extend(extra_args)
        kapitan(*argv)

    def _reveal_file(file_path, refs_path):
        return kapitan_stdout(
            "refs",
            "--reveal",
            "-f",
            str(file_path),
            "--refs-path",
            refs_path,
        )

    def _reveal_tag(tag, refs_path):
        return kapitan_stdout(
            "refs", "--reveal", "--tag", tag, "--refs-path", refs_path
        )

    def _reveal_ref_file(ref_file, refs_path):
        return kapitan_stdout(
            "refs",
            "--reveal",
            "--ref-file",
            str(ref_file),
            "--refs-path",
            refs_path,
        )

    return Namespace(
        write=_write,
        reveal_file=_reveal_file,
        reveal_tag=_reveal_tag,
        reveal_ref_file=_reveal_ref_file,
    )
