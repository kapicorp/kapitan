# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import multiprocessing.pool as mp
import os
from pathlib import Path

import pytest

from kapitan import cached
from kapitan.cached import reset_cache
from tests.support.paths import EXAMPLE_KUBERNETES_ROOT, KAPITAN_COMPILE_INTEGRATION
from tests.support.projects import copy_project_tree, prepare_isolated_project
from tests.support.runtime import cached_args_defaults


pytest_plugins = (
    "tests.support.fixtures.refs",
    "tests.support.fixtures.secrets",
)


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
def local_http_server(request, httpserver):
    """
    Expose pytest-httpserver to unittest.TestCase classes.
    """
    if request.cls is not None:
        request.cls.httpserver = httpserver
    return httpserver


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
