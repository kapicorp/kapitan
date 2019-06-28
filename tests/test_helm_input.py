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

"helm input tests"
import os
import sys
import unittest
import tempfile

from kapitan.cached import reset_cache
from kapitan.cli import main

helm_binding_exists = True
try:
    from kapitan.inputs.helm._template import ffi # this statement will raise ImportError if binding not available
    from kapitan.inputs.helm import render_chart
except ImportError:
    helm_binding_exists = False


@unittest.skipUnless(helm_binding_exists, "helm binding is not available")
class HelmInputTest(unittest.TestCase):
    def test_render_chart(self):
        temp_dir = tempfile.mkdtemp()
        chart_path = "./tests/test_resources/charts/acs-engine-autoscaler"
        error_message = render_chart(chart_path, temp_dir)

        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "secrets.yaml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "deployment.yaml")))
        self.assertFalse(error_message)

    def test_error_invalid_char_dir(self):
        chart_path = "non-existent"
        temp_dir = tempfile.mkdtemp()
        error_message = render_chart(chart_path, temp_dir)
        self.assertTrue("no such file or directory" in error_message)

    def test_compile_helm_input(self):
        cwd = os.getcwd()
        os.chdir(os.path.join(cwd, "tests", "test_resources"))
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "acs-engine-autoscaler", "nginx-ingress"]
        main()
        os.chdir(cwd)
        reset_cache()
        self.assertTrue(os.path.isfile(os.path.join(temp, "compiled", "acs-engine-autoscaler", "chart", "acs", "secrets.yaml")))

