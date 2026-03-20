#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Pytest configuration and shared fixtures for Kapitan tests.
Provides utilities for test isolation and parallel execution.
"""

import multiprocessing.pool as mp
import os
import shutil
import subprocess
import tempfile
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import pytest

from kapitan import cached
from kapitan.cached import reset_cache


# Base paths - these are read-only references
TEST_PWD = os.getcwd()
TEST_RESOURCES_PATH = os.path.join(TEST_PWD, "tests/test_resources")
TEST_DOCKER_PATH = os.path.join(TEST_PWD, "examples/docker/")
TEST_TERRAFORM_PATH = os.path.join(TEST_PWD, "examples/terraform/")
TEST_KUBERNETES_PATH = os.path.join(TEST_PWD, "examples/kubernetes/")


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
    cached.args = Namespace()
    yield
    reset_cache()
    cached.args = Namespace()


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
    cached.args = Namespace()

    # Create the isolated directory
    os.chdir(temp_dir)

    yield temp_dir

    # Cleanup
    os.chdir(original_dir)
    reset_cache()
    cached.args = Namespace()


@pytest.fixture
def isolated_test_resources(temp_dir, request):
    """
    Create an isolated copy of test_resources for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "test_resources")
    shutil.copytree(TEST_RESOURCES_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = Namespace()
    os.chdir(isolated_path)

    _attach_fixture(request, "isolated_test_resources", isolated_path)
    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = Namespace()


@pytest.fixture
def isolated_kubernetes_inventory(temp_dir):
    """
    Create an isolated copy of the kubernetes example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "kubernetes")
    shutil.copytree(TEST_KUBERNETES_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = Namespace()
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
    cached.args = Namespace()


@pytest.fixture
def isolated_terraform_inventory(temp_dir):
    """
    Create an isolated copy of the terraform example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "terraform")
    shutil.copytree(TEST_TERRAFORM_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = Namespace()
    os.chdir(isolated_path)

    # Safety check: ensure we're not in the actual examples directory
    assert "examples/terraform" not in isolated_path
    assert temp_dir in isolated_path

    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = Namespace()


@pytest.fixture
def isolated_docker_inventory(temp_dir):
    """
    Create an isolated copy of the docker example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = os.path.join(temp_dir, "docker")
    shutil.copytree(TEST_DOCKER_PATH, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = Namespace()
    os.chdir(isolated_path)

    # Safety check: ensure we're not in the actual examples directory
    assert "examples/docker" not in isolated_path
    assert temp_dir in isolated_path

    yield isolated_path

    os.chdir(original_dir)
    reset_cache()
    cached.args = Namespace()


@contextmanager
def isolated_compile_context(base_path: str, target_subdir: Optional[str] = None):
    """
    Context manager for isolated compilation.

    Args:
        base_path: Base path to copy for isolation
        target_subdir: Optional subdirectory to change to after copying

    Yields:
        Path to the isolated directory
    """
    temp_path = tempfile.mkdtemp(prefix="kapitan_compile_")
    isolated_path = os.path.join(temp_path, "test_env")
    shutil.copytree(base_path, isolated_path)

    original_dir = os.getcwd()
    reset_cache()
    cached.args = Namespace()

    # Change to target directory
    if target_subdir:
        work_dir = os.path.join(isolated_path, target_subdir)
    else:
        work_dir = isolated_path
    os.chdir(work_dir)

    # Clean any existing compiled directory in the ISOLATED copy only
    compiled_path = os.path.join(work_dir, "compiled")
    # Safety check: ensure we're not in the actual examples directory
    assert "examples/" not in work_dir or temp_path in work_dir
    if os.path.exists(compiled_path):
        shutil.rmtree(compiled_path)

    try:
        yield isolated_path
    finally:
        os.chdir(original_dir)
        shutil.rmtree(temp_path, ignore_errors=True)
        reset_cache()
        cached.args = Namespace()


@pytest.fixture
def refs_path(temp_dir):
    """Create an isolated refs path for secret management tests."""
    refs_dir = os.path.join(temp_dir, "refs")
    os.makedirs(refs_dir, exist_ok=True)
    return refs_dir


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


def ensure_compile_dirs_isolated():
    """
    Helper to ensure compile operations don't interfere with each other.
    Call this at the start of compile tests.
    """
    # Remove any existing compiled directory in current path
    if os.path.exists("compiled"):
        shutil.rmtree("compiled", ignore_errors=True)
    reset_cache()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "requires_gpg: mark test as requiring GPG setup")
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

    yield

    # Restore original state
    os.chdir(original_dir)
    os.environ.clear()
    os.environ.update(original_env)
    reset_cache()


@pytest.fixture
def setup_gpg_key():
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


@pytest.fixture
def local_http_server(request, httpserver):
    """
    Expose pytest-httpserver to unittest.TestCase classes.
    """
    if request.cls is not None:
        request.cls.httpserver = httpserver


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
