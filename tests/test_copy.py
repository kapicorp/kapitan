#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Copy tests refactored for pytest."""

import filecmp
import hashlib
import logging
import os

import pytest

from kapitan.inputs.copy import Copy
from kapitan.inventory.model.input_types import KapitanInputTypeCopyConfig
from kapitan.utils import directory_hash
from tests.test_helpers import CompileTestHelper

logger = logging.getLogger(__name__)


@pytest.fixture
def copy_test_setup(temp_dir):
    """Set up test directories and files for copy tests."""
    test_path = os.path.join(temp_dir, "test_copy")
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
def copy_compiler(copy_test_setup):
    """Create a Copy compiler instance for testing."""
    search_path = ""
    ref_controller = ""
    return Copy(copy_test_setup["compile_path"], search_path, ref_controller, "test", None)


class TestCopy:
    """Test basic copy functionality."""

    def test_copy_file_folder(self, copy_compiler, copy_test_setup):
        """Test copying a single file."""
        setup_test_dirs(copy_test_setup)

        config = KapitanInputTypeCopyConfig(
            input_paths=[copy_test_setup["test_file_path"]], output_path=copy_test_setup["compile_path"]
        )

        copy_compiler.compile_file(config, copy_test_setup["test_file_path"], copy_test_setup["compile_path"])

        # Verify file was copied correctly
        test_file_hash = hashlib.sha1(copy_test_setup["test_file_content"].encode()).digest()
        with open(copy_test_setup["test_file_compiled_path"]) as f:
            test_file_compiled_hash = hashlib.sha1(f.read().encode()).digest()

        assert test_file_hash == test_file_compiled_hash

    def test_copy_folder_folder(self, copy_compiler, copy_test_setup):
        """Test copying an entire folder."""
        setup_test_dirs(copy_test_setup)

        config = KapitanInputTypeCopyConfig(
            input_paths=[copy_test_setup["file_path"]], output_path=copy_test_setup["compile_path"]
        )

        copy_compiler.compile_file(config, copy_test_setup["file_path"], copy_test_setup["compile_path"])

        file_path_hash = directory_hash(copy_test_setup["file_path"])
        compile_path_hash = directory_hash(copy_test_setup["compile_path"])
        assert file_path_hash == compile_path_hash


class TestCopyMissingFile:
    """Test copy behavior with missing files."""

    def test_copy_missing_path_folder(self, copy_compiler, copy_test_setup):
        """Test copying a missing file path."""
        setup_test_dirs(copy_test_setup)

        test_file_missing_path = os.path.join(copy_test_setup["file_path"], "test_copy_input_missing")

        config = KapitanInputTypeCopyConfig(
            input_paths=[copy_test_setup["test_file_path"]], output_path=copy_test_setup["compile_path"]
        )

        copy_compiler.compile_file(config, test_file_missing_path, copy_test_setup["compile_path"])


class TestCompileCopy:
    """Test copy functionality through kapitan compile."""

    def validate_files_were_copied(self, isolated_path):
        """Helper to validate that files were copied correctly."""
        original_filepath = os.path.join(isolated_path, "components", "busybox", "pod.yml")
        copied_filepath = os.path.join(isolated_path, "compiled", "busybox", "copy", "pod.yml")
        assert filecmp.cmp(original_filepath, copied_filepath)

        original_filepath = os.path.join(isolated_path, "copy_target")
        copied_filepath = os.path.join(isolated_path, "compiled", "busybox", "copy", "copy_target")
        assert filecmp.cmp(original_filepath, copied_filepath)

        original_filepath = os.path.join(isolated_path, "copy_target")
        copied_filepath = os.path.join(isolated_path, "compiled", "busybox", "copy_target")
        assert filecmp.cmp(original_filepath, copied_filepath)

    def test_compiled_copy_target(self, isolated_kubernetes_inventory):
        """Test copying specific target through compile."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_targets(["busybox"])
        self.validate_files_were_copied(isolated_kubernetes_inventory)

    def test_compiled_copy_all_targets(self, isolated_kubernetes_inventory):
        """Test copying all targets through compile."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_with_args(["kapitan", "compile"])
        self.validate_files_were_copied(isolated_kubernetes_inventory)
