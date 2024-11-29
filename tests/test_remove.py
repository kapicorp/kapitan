#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"remove tests"
import os
import shutil
import sys
import unittest

from kapitan.cli import main
from kapitan.inputs.copy import Copy
from kapitan.inputs.remove import Remove
from kapitan.inventory.model.input_types import (
    KapitanInputTypeCopyConfig,
    KapitanInputTypeRemoveConfig,
)

search_path = ""
ref_controller = ""
test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_remove")
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


def test_dirs_bootstrap_helper():
    for folder in [file_path, compile_path]:
        os.makedirs(folder, exist_ok=True)
        with open(test_file_path, "w") as f:
            f.write(test_file_content)


class RemoveTest(unittest.TestCase):
    def setUp(self):
        try:
            shutil.rmtree(test_path)
        except FileNotFoundError:
            pass

        self.copy_compiler = Copy(compile_path, search_path, ref_controller, None, None)
        self.remove_compiler = Remove(compile_path, search_path, ref_controller, None, None)

    def test_remove_file_folder(self):
        test_dirs_bootstrap_helper()

        copy_config = KapitanInputTypeCopyConfig(input_paths=[file_path], output_path="")
        self.copy_compiler.compile_file(copy_config, test_file_path, compile_path)

        self.assertTrue(os.path.exists(test_file_compiled_path))

        remove_config = KapitanInputTypeRemoveConfig(input_paths=[test_file_compiled_path])
        self.remove_compiler.compile_file(remove_config, test_file_compiled_path, compile_path)
        self.assertFalse(os.path.exists(test_file_compiled_path))

    def test_remove_folder_folder(self):
        test_dirs_bootstrap_helper()

        copy_config = KapitanInputTypeCopyConfig(input_paths=[file_path], output_path="")
        self.copy_compiler.compile_file(copy_config, test_file_path, compile_path)

        self.assertTrue(os.path.exists(compile_path))
        remove_config = KapitanInputTypeRemoveConfig(input_paths=[test_file_compiled_path])
        self.remove_compiler.compile_file(remove_config, compile_path, compile_path)
        self.assertFalse(os.path.exists(compile_path))

    def tearDown(self):
        try:
            shutil.rmtree(test_path)
        except FileNotFoundError:
            pass


class CompileRemoveTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join(os.getcwd(), "examples", "kubernetes"))

    def validate_files_were_removed(self):
        original_filepath = os.path.join("copy_target")
        self.assertTrue(os.path.exists(original_filepath))
        removed_file = os.path.join("compiled", "removal", "copy_target")
        self.assertFalse(os.path.exists(removed_file))

    def test_compiled_remove_target(self):
        sys.argv = ["kapitan", "compile", "-t", "removal"]
        main()
        self.validate_files_were_removed()

    def tearDown(self):
        os.chdir(os.path.join(os.getcwd(), "..", ".."))
