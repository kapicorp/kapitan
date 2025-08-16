#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Remove tests refactored for pytest."""

import os

import pytest

from kapitan.inputs.copy import Copy
from kapitan.inputs.remove import Remove
from kapitan.inventory.model.input_types import (
    KapitanInputTypeCopyConfig,
    KapitanInputTypeRemoveConfig,
)
from tests.test_helpers import CompileTestHelper


@pytest.fixture
def remove_test_setup(temp_dir):
    """Set up test directories and files for remove tests."""
    test_path = os.path.join(temp_dir, "test_remove")
    compile_path = os.path.join(test_path, "output")
    file_path = os.path.join(test_path, "input")
    test_file_path = os.path.join(file_path, "test_copy_input")
    test_file_compiled_path = os.path.join(compile_path, "test_copy_input")

    test_file_content = """
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

    return {
        "test_path": test_path,
        "compile_path": compile_path,
        "file_path": file_path,
        "test_file_path": test_file_path,
        "test_file_compiled_path": test_file_compiled_path,
        "test_file_content": test_file_content,
    }


def setup_test_dirs(setup):
    """Helper to bootstrap test directories and files."""
    for folder in [setup["file_path"], setup["compile_path"]]:
        os.makedirs(folder, exist_ok=True)

    with open(setup["test_file_path"], "w") as f:
        f.write(setup["test_file_content"])


@pytest.fixture
def compilers(remove_test_setup):
    """Create Copy and Remove compiler instances for testing."""
    search_path = ""
    ref_controller = ""

    copy_compiler = Copy(remove_test_setup["compile_path"], search_path, ref_controller, None, None)

    remove_compiler = Remove(remove_test_setup["compile_path"], search_path, ref_controller, None, None)

    return {
        "copy_compiler": copy_compiler,
        "remove_compiler": remove_compiler,
    }


class TestRemove:
    """Test remove functionality."""

    def test_remove_file_folder(self, compilers, remove_test_setup):
        """Test removing a single file after copying it."""
        setup_test_dirs(remove_test_setup)

        # First copy a file
        copy_config = KapitanInputTypeCopyConfig(input_paths=[remove_test_setup["file_path"]], output_path="")
        compilers["copy_compiler"].compile_file(
            copy_config, remove_test_setup["test_file_path"], remove_test_setup["compile_path"]
        )

        assert os.path.exists(remove_test_setup["test_file_compiled_path"])

        # Then remove it
        remove_config = KapitanInputTypeRemoveConfig(
            input_paths=[remove_test_setup["test_file_compiled_path"]]
        )
        compilers["remove_compiler"].compile_file(
            remove_config, remove_test_setup["test_file_compiled_path"], remove_test_setup["compile_path"]
        )

        assert not os.path.exists(remove_test_setup["test_file_compiled_path"])

    def test_remove_folder_folder(self, compilers, remove_test_setup):
        """Test removing an entire folder after copying it."""
        setup_test_dirs(remove_test_setup)

        # First copy a file
        copy_config = KapitanInputTypeCopyConfig(input_paths=[remove_test_setup["file_path"]], output_path="")
        compilers["copy_compiler"].compile_file(
            copy_config, remove_test_setup["test_file_path"], remove_test_setup["compile_path"]
        )

        assert os.path.exists(remove_test_setup["compile_path"])

        # Then remove the entire compile directory
        remove_config = KapitanInputTypeRemoveConfig(
            input_paths=[remove_test_setup["test_file_compiled_path"]]
        )
        compilers["remove_compiler"].compile_file(
            remove_config, remove_test_setup["compile_path"], remove_test_setup["compile_path"]
        )

        assert not os.path.exists(remove_test_setup["compile_path"])


class TestCompileRemove:
    """Test remove functionality through kapitan compile."""

    def validate_files_were_removed(self, isolated_path):
        """Helper to validate that files were removed correctly."""
        original_filepath = os.path.join(isolated_path, "copy_target")
        assert os.path.exists(original_filepath)

        removed_file = os.path.join(isolated_path, "compiled", "removal", "copy_target")
        assert not os.path.exists(removed_file)

    def test_compiled_remove_target(self, isolated_kubernetes_inventory):
        """Test removing files through compile."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_targets(["removal"])
        self.validate_files_were_removed(isolated_kubernetes_inventory)
