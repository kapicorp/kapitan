#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"copy tests"

import filecmp
import hashlib
import os
import unittest

import pytest

from kapitan.cli import main as kapitan
from kapitan.inputs.copy import Copy
from kapitan.inventory.model.input_types import KapitanInputTypeCopyConfig
from kapitan.utils import directory_hash


TEST_FILE_CONTENT = """
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


def dirs_bootstrap_helper(base_path: str):
    file_path = os.path.join(base_path, "input")
    compile_path = os.path.join(base_path, "output")
    os.makedirs(file_path, exist_ok=True)
    os.makedirs(compile_path, exist_ok=True)
    test_file_path = os.path.join(file_path, "test_copy_input")
    with open(test_file_path, "w") as f:
        f.write(TEST_FILE_CONTENT)
    return file_path, compile_path, test_file_path


@pytest.mark.usefixtures("isolated_compile_dir")
class CopyTest(unittest.TestCase):
    def setUp(self):
        self.base_path = os.getcwd()

    def test_copy_file_folder(self):
        file_path, compile_path, test_file_path = dirs_bootstrap_helper(self.base_path)
        test_file_compiled_path = os.path.join(compile_path, "test_copy_input")
        copy_compiler = Copy(compile_path, "", "", "test", None)
        config = KapitanInputTypeCopyConfig(
            input_paths=[test_file_path], output_path=compile_path
        )
        copy_compiler.compile_file(config, test_file_path, compile_path)
        test_file_hash = hashlib.sha1(TEST_FILE_CONTENT.encode()).digest()
        with open(test_file_compiled_path) as f:
            test_file_compiled_hash = hashlib.sha1(f.read().encode()).digest()
            self.assertEqual(test_file_hash, test_file_compiled_hash)

    def test_copy_folder_folder(self):
        file_path, compile_path, _ = dirs_bootstrap_helper(self.base_path)
        copy_compiler = Copy(compile_path, "", "", "test", None)
        config = KapitanInputTypeCopyConfig(
            input_paths=[file_path], output_path=compile_path
        )
        copy_compiler.compile_file(config, file_path, compile_path)
        file_path_hash = directory_hash(file_path)
        compile_path_hash = directory_hash(compile_path)
        self.assertEqual(file_path_hash, compile_path_hash)


@pytest.mark.usefixtures("isolated_compile_dir")
class CopyMissingFileTest(unittest.TestCase):
    def test_copy_missing_path_folder(self):
        file_path, compile_path, test_file_path = dirs_bootstrap_helper(os.getcwd())
        copy_compiler = Copy(compile_path, "", "", "test", None)
        test_file_missing_path = os.path.join(file_path, "test_copy_input_missing")
        config = KapitanInputTypeCopyConfig(
            input_paths=[test_file_path], output_path=compile_path
        )
        copy_compiler.compile_file(config, test_file_missing_path, compile_path)


@pytest.mark.usefixtures("isolated_kubernetes_inventory")
class CompileCopyTest(unittest.TestCase):
    def _validate_files_were_copied(self, base_path: str) -> None:
        original_filepath = os.path.join(base_path, "components", "busybox", "pod.yml")
        copied_filepath = os.path.join(
            base_path, "compiled", "busybox", "copy", "pod.yml"
        )
        self.assertTrue(filecmp.cmp(original_filepath, copied_filepath))

        original_filepath = os.path.join(base_path, "copy_target")
        copied_filepath = os.path.join(
            base_path, "compiled", "busybox", "copy", "copy_target"
        )
        self.assertTrue(filecmp.cmp(original_filepath, copied_filepath))

        original_filepath = os.path.join(base_path, "copy_target")
        copied_filepath = os.path.join(base_path, "compiled", "busybox", "copy_target")
        self.assertTrue(filecmp.cmp(original_filepath, copied_filepath))

    def test_compiled_copy_target(self):
        kapitan("compile", "-t", "busybox")
        self._validate_files_were_copied(os.getcwd())

    def test_compiled_copy_all_targets(self):
        kapitan("compile")
        self._validate_files_were_copied(os.getcwd())
