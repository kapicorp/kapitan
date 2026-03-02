# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import subprocess
import tempfile
from pathlib import Path

import pytest

from kapitan import cached
from tests.support.paths import EXAMPLE_KUBERNETES_ROOT


@pytest.fixture
def gnupg_home(monkeypatch):
    """
    Create an isolated GNUPGHOME for GPG tests.
    Use a short temp path because gpg-agent socket paths are length-sensitive.
    """
    with tempfile.TemporaryDirectory(prefix="kgpg_") as temp_dir:
        gnupg_dir = Path(temp_dir) / "gnupg"
        gnupg_dir.mkdir(mode=0o700)
        monkeypatch.setenv("GNUPGHOME", str(gnupg_dir))
        yield str(gnupg_dir)


@pytest.fixture
def gpg_env(gnupg_home):
    from kapitan.refs.secrets.gpg import gpg_obj

    cached.gpg_obj = None
    gpg_obj(gnupghome=gnupg_home)
    return gnupg_home


@pytest.fixture
def setup_gpg_key(gpg_env):
    example_key = EXAMPLE_KUBERNETES_ROOT / "refs" / "example@kapitan.dev.key"

    subprocess.run(["gpg", "--import", str(example_key)], check=True)

    ownertrust = b"D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C:6\n"

    subprocess.run(
        ["gpg", "--import-ownertrust"],
        input=ownertrust,
        check=True,
    )
    cached.gpg_obj = None


@pytest.fixture(scope="module")
def vault_server():
    from tests.support.vault_server import VaultServer

    server = VaultServer()
    yield server
    server.close_container()
