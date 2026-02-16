# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
import io
import multiprocessing.pool as mp
import os
import shutil
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

from kapitan import cached
from kapitan.cached import reset_cache
from tests.support.paths import (
    EXAMPLE_DOCKER_ROOT,
    EXAMPLE_KUBERNETES_ROOT,
    EXAMPLE_TERRAFORM_ROOT,
    KAPITAN_COMPILE_INTEGRATION,
    KAPITAN_HELM_INTEGRATION,
    KAPITAN_LINT_FIXTURE,
)


# Base paths - these are read-only references
_TEST_COMPILE_PROJECT_PATH = str(KAPITAN_COMPILE_INTEGRATION)
_TEST_HELM_PROJECT_PATH = str(KAPITAN_HELM_INTEGRATION)
_TEST_LINT_PROJECT_PATH = str(KAPITAN_LINT_FIXTURE)
_TEST_DOCKER_PATH = str(EXAMPLE_DOCKER_ROOT)
_TEST_TERRAFORM_PATH = str(EXAMPLE_TERRAFORM_ROOT)
_TEST_KUBERNETES_PATH = str(EXAMPLE_KUBERNETES_ROOT)


def _cached_args_defaults(**overrides):
    args = {"cache": False}
    args.update(overrides)
    return Namespace(**args)


@pytest.fixture
def temp_dir():
    """Create a temporary directory that is automatically cleaned up."""
    temp_path = tempfile.mkdtemp(prefix="kapitan_test_")
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def reset_cached_args():
    """
    Reset cached globals and args to avoid backend leakage between tests.
    """
    reset_cache()
    cached.args = _cached_args_defaults()
    yield
    reset_cache()
    cached.args = _cached_args_defaults()


def _attach_fixture(request, name, value):
    instance = getattr(request, "instance", None)
    if instance is not None:
        setattr(instance, name, value)


@pytest.fixture
def isolated_compile_dir(temp_dir):
    """
    Create an isolated compilation directory with its own compiled/ output.
    Automatically resets cache and returns to original directory after test.
    """
    original_dir = os.getcwd()
    reset_cache()
    cached.args = _cached_args_defaults()

    # Create the isolated directory
    os.chdir(temp_dir)

    yield temp_dir

    # Cleanup
    os.chdir(original_dir)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def isolated_test_resources(temp_dir, request):
    """
    Create an isolated copy of the compile fixture project for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "compile_project")
    shutil.copytree(_TEST_COMPILE_PROJECT_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = _cached_args_defaults()
    os.chdir(isolated_path)

    _attach_fixture(request, "isolated_test_resources", isolated_path)
    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def isolated_helm_project(temp_dir):
    """
    Create an isolated copy of the helm fixture project for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "helm_project")
    shutil.copytree(_TEST_HELM_PROJECT_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = _cached_args_defaults()
    os.chdir(isolated_path)

    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def isolated_lint_project(temp_dir):
    """
    Create an isolated copy of the lint fixture project for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "lint_project")
    shutil.copytree(_TEST_LINT_PROJECT_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = _cached_args_defaults()
    os.chdir(isolated_path)

    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def isolated_kubernetes_inventory(temp_dir):
    """
    Create an isolated copy of the kubernetes example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "kubernetes")
    shutil.copytree(_TEST_KUBERNETES_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = _cached_args_defaults()
    os.chdir(isolated_path)

    # Clean any existing compiled directory in the ISOLATED copy only
    compiled_path = os.path.join(isolated_path, "compiled")
    # Safety check: ensure we're not in the actual examples directory
    assert "examples/kubernetes" not in isolated_path
    assert temp_dir in isolated_path
    if os.path.exists(compiled_path):
        shutil.rmtree(compiled_path)

    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def isolated_terraform_inventory(temp_dir):
    """
    Create an isolated copy of the terraform example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "terraform")
    shutil.copytree(_TEST_TERRAFORM_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = _cached_args_defaults()
    os.chdir(isolated_path)

    # Safety check: ensure we're not in the actual examples directory
    assert "examples/terraform" not in isolated_path
    assert temp_dir in isolated_path

    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def isolated_docker_inventory(temp_dir):
    """
    Create an isolated copy of the docker example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "docker")
    shutil.copytree(_TEST_DOCKER_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = _cached_args_defaults()
    os.chdir(isolated_path)

    # Safety check: ensure we're not in the actual examples directory
    assert "examples/docker" not in isolated_path
    assert temp_dir in isolated_path

    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def kubernetes_inventory_copy(temp_dir):
    """
    Create a writable copy of the kubernetes example without changing cwd.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "kubernetes")
    shutil.copytree(_TEST_KUBERNETES_PATH, isolated_path)
    return isolated_path


@pytest.fixture
def migrated_omegaconf_inventory(kubernetes_inventory_copy):
    """
    Return a migrated omegaconf inventory path under a writable copy.
    """
    from kapitan.inventory.backends.omegaconf import migrate
    from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers

    inventory_path = os.path.join(kubernetes_inventory_copy, "inventory")
    migrate(inventory_path)
    register_resolvers()
    return inventory_path


@pytest.fixture
def refs_path(temp_dir):
    """Create an isolated refs path for secret management tests."""
    refs_dir = os.path.join(temp_dir, "refs")
    os.makedirs(refs_dir, exist_ok=True)
    return refs_dir


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
            # Avoid sharing a mutable list between test calls.
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
def targets_compile_args():
    """Factory for kapitan.targets.compile_targets args."""
    defaults = {
        "targets": None,
        "labels": None,
        "parallelism": 1,
        "force_fetch": False,
        "fetch": False,
        "force": False,
        "output_path": None,
        "inventory_pool_cache": False,
        "verbose": False,
    }

    def _make(**overrides):
        args = defaults.copy()
        args.update(overrides)
        return Namespace(**args)

    return _make


@pytest.fixture
def input_args():
    """Factory for common input compiler args."""
    defaults = {
        "cache": False,
        "reveal": False,
        "indent": 2,
    }

    def _make(**overrides):
        args = defaults.copy()
        args.update(overrides)
        return Namespace(**args)

    return _make


@pytest.fixture
def restore_cached_state():
    """Restore kapitan.cached module state after test mutation."""
    state = cached.as_dict()
    yield
    cached.from_dict(state)


@pytest.fixture
def sample_pod_manifest():
    return """\
apiVersion: v1
kind: Pod
metadata:
  name: alpine
  namespace: default
spec:
  containers:
  - image: alpine:3.2
    command:
      - /bin/sh
      - "-c"
      - "sleep 60m"
    imagePullPolicy: IfNotPresent
    name: alpine
  restartPolicy: Always
"""


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

    # Restore original GNUPGHOME
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
    cached.args = _cached_args_defaults()

    yield

    # Restore original state
    os.chdir(original_dir)
    os.environ.clear()
    os.environ.update(original_env)
    reset_cache()
    cached.args = _cached_args_defaults()


@pytest.fixture
def setup_gpg_key(gpg_env):
    example_key = "examples/kubernetes/refs/example@kapitan.dev.key"
    example_key = os.path.join(os.getcwd(), example_key)

    subprocess.run(["gpg", "--import", example_key], check=True)

    # always trust this key - for testing only!
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
    from kapitan import cached
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
