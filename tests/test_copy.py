#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"copy tests"
import os
import sys
import shutil
import hashlib
import unittest

from kapitan.cli import main
from kapitan.utils import directory_hash
from kapitan.inputs.copy import Copy


search_path = ""
ref_controller = ""
test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_copy")
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


class CopyTest(unittest.TestCase):
    def setUp(self):
        try:
            shutil.rmtree(test_path)
        except FileNotFoundError:
            pass

        self.copy_compiler = Copy(compile_path, search_path, ref_controller)

    def test_copy_file_folder(self):
        test_dirs_bootstrap_helper()
        self.copy_compiler.compile_file(test_file_path, compile_path, None)
        self.test_file_hash = hashlib.sha1(test_file_content.encode()).digest()
        with open(test_file_compiled_path) as f:
            test_file_compiled_hash = hashlib.sha1(f.read().encode()).digest()
            self.assertEqual(self.test_file_hash, test_file_compiled_hash)

    def test_copy_folder_folder(self):
        test_dirs_bootstrap_helper()
        self.copy_compiler.compile_file(file_path, compile_path, None)
        file_path_hash = directory_hash(file_path)
        compile_path_hash = directory_hash(compile_path)
        self.assertEqual(file_path_hash, compile_path_hash)

    def tearDown(self):
        try:
            shutil.rmtree(test_path)
        except FileNotFoundError:
            pass


class CompileCopyTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join(os.getcwd(), "examples", "kubernetes"))

    def test_compiled_copy_target(self):
        sys.argv = ["kapitan", "compile", "-t", "busybox"]
        main()
        file_path_hash = directory_hash(os.path.join("components", "busybox"))
        compile_path_hash = directory_hash(os.path.join("compiled", "busybox", "copy"))
        self.assertEqual(file_path_hash, compile_path_hash)

    def test_compiled_copy_all_targets(self):
        sys.argv = ["kapitan", "compile"]
        main()
        file_path_hash = directory_hash(os.path.join("components", "busybox"))
        compile_path_hash = directory_hash(os.path.join("compiled", "busybox", "copy"))
        self.assertEqual(file_path_hash, compile_path_hash)

    def tearDown(self):
        os.chdir(os.path.join(os.getcwd(), "..", ".."))
