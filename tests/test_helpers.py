#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Helper utilities for Kapitan tests.
Provides common functionality for test isolation and execution.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

import yaml

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan
from kapitan.utils import directory_hash


class CompileTestHelper:
    """Helper class for compilation tests."""

    def __init__(self, isolated_path: str):
        """
        Initialize compile test helper.

        Args:
            isolated_path: Path to isolated test directory
        """
        self.isolated_path = isolated_path
        self.original_dir = os.getcwd()

    def compile_targets(
        self,
        targets: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> None:
        """
        Compile specified targets or all targets.

        Args:
            targets: List of target names to compile (None for all)
            extra_args: Additional command line arguments
        """
        reset_cache()

        args = ["compile"]

        if targets:
            for target in targets:
                args.extend(["-t", target])

        if extra_args:
            args.extend(extra_args)

        kapitan(*args)

    def compile_with_args(self, argv: List[str]) -> None:
        """
        Compile with custom arguments.

        Args:
            argv: Command arguments for kapitan (without the program name)
        """
        reset_cache()
        kapitan(*argv)

    def get_compiled_output(self, relative_path: str) -> str:
        """
        Read compiled output file.

        Args:
            relative_path: Path relative to compiled/ directory

        Returns:
            File contents as string
        """
        compiled_path = os.path.join(self.isolated_path, "compiled", relative_path)
        with open(compiled_path) as f:
            return f.read()

    def verify_compiled_output_exists(self, relative_path: str) -> bool:
        """
        Check if compiled output exists.

        Args:
            relative_path: Path relative to compiled/ directory

        Returns:
            True if file exists
        """
        compiled_path = os.path.join(self.isolated_path, "compiled", relative_path)
        return os.path.exists(compiled_path)

    def compare_compiled_dirs(self, expected_dir: str) -> bool:
        """
        Compare compiled output with expected directory.

        Args:
            expected_dir: Path to expected output directory

        Returns:
            True if directories match
        """
        compiled_dir = os.path.join(self.isolated_path, "compiled")
        compiled_hash = directory_hash(compiled_dir)
        expected_hash = directory_hash(expected_dir)
        return compiled_hash == expected_hash


class IsolatedTestEnvironment:
    """
    Context manager for creating isolated test environments.
    """

    def __init__(self, base_path: str, copy_base: bool = True):
        """
        Initialize isolated environment.

        Args:
            base_path: Base path to use or copy
            copy_base: Whether to copy base_path to temp location
        """
        self.base_path = base_path
        self.copy_base = copy_base
        self.temp_dir = None
        self.work_dir = None
        self.original_dir = os.getcwd()

    def __enter__(self):
        """Enter the isolated environment."""
        reset_cache()

        if self.copy_base:
            self.temp_dir = tempfile.mkdtemp(prefix="kapitan_test_")
            self.work_dir = os.path.join(self.temp_dir, "work")
            shutil.copytree(self.base_path, self.work_dir)
        else:
            self.work_dir = self.base_path

        os.chdir(self.work_dir)

        # Clean any existing compiled directory
        compiled_path = os.path.join(self.work_dir, "compiled")
        if os.path.exists(compiled_path):
            shutil.rmtree(compiled_path)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the isolated environment and cleanup."""
        os.chdir(self.original_dir)

        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

        reset_cache()

    @property
    def path(self) -> str:
        """Get the working directory path."""
        return self.work_dir


def setup_gpg_key(key_path: str, gnupg_home: Optional[str] = None) -> None:
    """
    Import a GPG key for testing.

    Args:
        key_path: Path to the GPG key file
        gnupg_home: Optional GNUPGHOME directory
    """
    env = os.environ.copy()
    if gnupg_home:
        env["GNUPGHOME"] = gnupg_home

    # Import the key
    subprocess.run(["gpg", "--import", key_path], env=env, check=True)

    # Get key fingerprint
    result = subprocess.run(
        ["gpg", "--list-secret-keys", "--with-colons"],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )

    # Trust the key (for testing only!)
    for line in result.stdout.split("\n"):
        if line.startswith("fpr:"):
            fingerprint = line.split(":")[9]
            trust_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
            trust_file.write(f"{fingerprint}:6\n")
            trust_file.close()

            subprocess.run(
                ["gpg", "--import-ownertrust", trust_file.name], env=env, check=True
            )
            os.unlink(trust_file.name)
            break


def create_test_inventory(temp_dir: str, targets: Dict[str, Any]) -> str:
    """
    Create a minimal test inventory structure.

    Args:
        temp_dir: Temporary directory to create inventory in
        targets: Dictionary of target configurations

    Returns:
        Path to the inventory directory
    """
    inventory_dir = os.path.join(temp_dir, "inventory")
    targets_dir = os.path.join(inventory_dir, "targets")
    classes_dir = os.path.join(inventory_dir, "classes")

    os.makedirs(targets_dir)
    os.makedirs(classes_dir)

    # Create target files
    for target_name, target_config in targets.items():
        target_file = os.path.join(targets_dir, f"{target_name}.yml")
        with open(target_file, "w") as f:
            yaml.dump(target_config, f)

    # Create a basic common class
    common_class = {"parameters": {"kapitan": {"compile": []}}}
    with open(os.path.join(classes_dir, "common.yml"), "w") as f:
        yaml.dump(common_class, f)

    return inventory_dir


@contextlib.contextmanager
def capture_output():
    """
    Context manager to capture stdout and stderr.

    Yields:
        Tuple of (stdout, stderr) StringIO objects
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    stdout = io.StringIO()
    stderr = io.StringIO()

    sys.stdout = stdout
    sys.stderr = stderr

    try:
        yield stdout, stderr
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def run_kapitan_command(args: List[str]) -> tuple[int, str, str]:
    """
    Run a kapitan command and capture output.

        Args:
            args: Command arguments for kapitan (without the program name)

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    with capture_output() as (stdout, stderr):
        exit_code = 0
        try:
            kapitan(*args)
        except SystemExit as e:
            exit_code = e.code if e.code is not None else 0

    return exit_code, stdout.getvalue(), stderr.getvalue()


def assert_file_contains(file_path: str, expected_content: str) -> None:
    """
    Assert that a file contains expected content.

    Args:
        file_path: Path to file to check
        expected_content: Expected content substring

    Raises:
        AssertionError: If content not found
    """
    with open(file_path) as f:
        content = f.read()
        assert (
            expected_content in content
        ), f"Expected '{expected_content}' not found in {file_path}"


def assert_file_not_contains(file_path: str, unexpected_content: str) -> None:
    """
    Assert that a file does not contain unexpected content.

    Args:
        file_path: Path to file to check
        unexpected_content: Content that should not be present

    Raises:
        AssertionError: If content is found
    """
    with open(file_path) as f:
        content = f.read()
        assert (
            unexpected_content not in content
        ), f"Unexpected '{unexpected_content}' found in {file_path}"
