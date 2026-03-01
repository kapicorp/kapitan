# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
import io
import multiprocessing.pool as mp
import os
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

from kapitan import cached
from kapitan.cached import reset_cache
from tests.support.paths import EXAMPLE_KUBERNETES_ROOT, KAPITAN_COMPILE_INTEGRATION
from tests.support.projects import copy_project_tree, prepare_isolated_project
from tests.support.runtime import cached_args_defaults


@pytest.fixture
def temp_dir():
    """Create a temporary directory that is automatically cleaned up."""
    temp_path = tempfile.mkdtemp(prefix="kapitan_test_")
    yield temp_path
    from shutil import rmtree

    rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def reset_cached_args():
    """
    Reset cached globals and args to avoid backend leakage between tests.
    """
    reset_cache()
    cached.args = cached_args_defaults()
    yield
    reset_cache()
    cached.args = cached_args_defaults()


def _attach_fixture(request, name, value):
    instance = getattr(request, "instance", None)
    if instance is not None:
        setattr(instance, name, value)


@pytest.fixture
def isolated_test_resources(tmp_path, monkeypatch, request):
    """
    Create an isolated copy of the compile fixture project for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = prepare_isolated_project(
        tmp_path, monkeypatch, KAPITAN_COMPILE_INTEGRATION, "compile_project"
    )
    _attach_fixture(request, "isolated_test_resources", isolated_path)
    return isolated_path


@pytest.fixture
def isolated_kubernetes_inventory(tmp_path, monkeypatch):
    """
    Create an isolated copy of the kubernetes example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = prepare_isolated_project(
        tmp_path,
        monkeypatch,
        EXAMPLE_KUBERNETES_ROOT,
        "kubernetes",
        clean_compiled=True,
    )
    compiled_path = isolated_path / "compiled"
    # Safety check: ensure we're not in the actual examples directory
    assert EXAMPLE_KUBERNETES_ROOT not in isolated_path.parents
    assert tmp_path in isolated_path.parents
    if compiled_path.exists():
        from shutil import rmtree

        rmtree(compiled_path)
    return isolated_path


@pytest.fixture
def kubernetes_inventory_copy(tmp_path):
    """
    Create a writable copy of the kubernetes example without changing cwd.
    Returns the path to the isolated copy.
    """
    return copy_project_tree(tmp_path, EXAMPLE_KUBERNETES_ROOT, "kubernetes")


@pytest.fixture
def migrated_omegaconf_inventory(kubernetes_inventory_copy):
    """
    Return a migrated omegaconf inventory path under a writable copy.
    """
    from kapitan.inventory.backends.omegaconf import migrate
    from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers

    inventory_path = Path(kubernetes_inventory_copy) / "inventory"
    migrate(str(inventory_path))
    register_resolvers()
    return inventory_path


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


@pytest.fixture
def gnupg_home(temp_dir):
    """
    Create an isolated GNUPGHOME for GPG tests.
    Sets and restores the GNUPGHOME environment variable.
    """
    gnupg_dir = os.path.join(temp_dir, "gnupg")
    os.makedirs(gnupg_dir, mode=0o700)

    original_gnupghome = os.environ.get("GNUPGHOME")
    os.environ["GNUPGHOME"] = gnupg_dir

    yield gnupg_dir

    if original_gnupghome:
        os.environ["GNUPGHOME"] = original_gnupghome
    else:
        os.environ.pop("GNUPGHOME", None)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "requires_gpg: mark test as requiring GPG setup")
    config.addinivalue_line(
        "markers", "requires_helm: mark test as requiring helm binary"
    )
    config.addinivalue_line(
        "markers", "requires_kustomize: mark test as requiring kustomize binary"
    )
    config.addinivalue_line(
        "markers", "requires_cue: mark test as requiring cue binary"
    )
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
    config.addinivalue_line(
        "markers", "requires_vault: mark test as requiring Vault server"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.fixture(scope="session", autouse=True)
def graceful_multiprocessing_pool_exit():
    # Pool.__exit__ calls terminate() unconditionally, which can corrupt
    # coverage data files. Patch to close/join on success during tests.
    original_exit = mp.Pool.__exit__

    def _graceful_exit(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.close()
            self.join()
        else:
            self.terminate()

    mp.Pool.__exit__ = _graceful_exit
    yield
    mp.Pool.__exit__ = original_exit


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Automatically reset the environment before and after each test.
    This ensures tests don't affect each other.
    """
    original_dir = os.getcwd()
    original_env = os.environ.copy()
    cached.args = cached_args_defaults()

    yield

    # Restore original state
    os.chdir(original_dir)
    os.environ.clear()
    os.environ.update(original_env)
    reset_cache()
    cached.args = cached_args_defaults()


@pytest.fixture
def setup_gpg_key(gpg_env):
    example_key = "examples/kubernetes/refs/example@kapitan.dev.key"
    example_key = os.path.join(os.getcwd(), example_key)

    subprocess.run(["gpg", "--import", example_key], check=True)

    ownertrust = b"D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C:6\n"

    subprocess.run(
        ["gpg", "--import-ownertrust"],
        input=ownertrust,
        check=True,
    )
    cached.gpg_obj = None


@pytest.fixture
def local_http_server(request, httpserver):
    """
    Expose pytest-httpserver to unittest.TestCase classes.
    """
    if request.cls is not None:
        request.cls.httpserver = httpserver
    return httpserver


@pytest.fixture
def gpg_env(gnupg_home):
    from kapitan.refs.secrets.gpg import gpg_obj

    cached.gpg_obj = None
    gpg_obj(gnupghome=gnupg_home)
    return gnupg_home


@pytest.fixture(scope="module")
def vault_server():
    from tests.support.vault_server import VaultServer

    server = VaultServer()
    yield server
    server.close_container()


@pytest.fixture
def seeded_git_repo(git_repo, request):
    repo = git_repo.api
    repo_path = Path(repo.working_tree_dir)

    readme = repo_path / "README.md"
    readme.write_text("kapitan test repo\n", encoding="utf-8")

    tests_dir = repo_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    subdir_file = tests_dir / "subdir.txt"
    subdir_file.write_text("subdir content\n", encoding="utf-8")

    repo.index.add(["README.md", "tests/subdir.txt"])

    if repo.is_dirty(untracked_files=True):
        repo.index.commit("initial commit")

    repo.git.branch("-M", "master")

    _attach_fixture(request, "seeded_git_repo", repo_path)

    return repo_path
