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
from tests.support.runtime import cached_args_defaults


pytest_plugins = (
    "tests.support.fixtures.projects",
    "tests.support.fixtures.refs",
    "tests.support.fixtures.secrets",
)


@pytest.fixture
def reset_cached_args():
    """
    Reset cached globals and args to avoid backend leakage between tests.
    """
    _reset_cached_runtime()
    yield
    _reset_cached_runtime()


def _reset_cached_runtime():
    reset_cache()
    cached.args = cached_args_defaults()


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
def restore_environment():
    """
    Restore environment variables around each test.
    """
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def reset_cached_runtime():
    """
    Reset cached globals around each test.
    """
    _reset_cached_runtime()
    yield
    _reset_cached_runtime()


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

    instance = getattr(request, "instance", None)
    if instance is not None:
        instance.seeded_git_repo = repo_path

    return repo_path
