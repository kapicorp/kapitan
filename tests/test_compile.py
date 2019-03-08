#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"compile tests"

import unittest
import os
import sys
import io
import contextlib
from kapitan.cli import main
from kapitan.utils import directory_hash
from kapitan.cached import reset_cache


class CompileKubernetesTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + '/examples/kubernetes/')

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-c"]
        main()
        os.remove('./compiled/.kapitan_cache')
        compiled_dir_hash = directory_hash(os.getcwd() + '/compiled')
        test_compiled_dir_hash = directory_hash(os.getcwd() + '/../../tests/test_kubernetes_compiled')
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def test_compile_not_enough_args(self):
        with self.assertRaises(SystemExit) as cm:
            # Ignoring stdout for "kapitan --help"
            with contextlib.redirect_stdout(io.StringIO()):
                sys.argv = ["kapitan"]
                main()
        self.assertEqual(cm.exception.code, 1)

    def tearDown(self):
        os.chdir(os.getcwd() + '/../../')
        reset_cache()


class CompileTerraformTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + '/examples/terraform/')

    def test_compile(self):
        sys.argv = ["kapitan", "compile"]
        main()
        compiled_dir_hash = directory_hash(os.getcwd() + '/compiled')
        test_compiled_dir_hash = directory_hash(
            os.getcwd() + '/../../tests/test_terraform_compiled')
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def tearDown(self):
        os.chdir(os.getcwd() + '/../../')
        reset_cache()
