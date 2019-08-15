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
import yaml

from kapitan.cached import reset_cache
from kapitan.cli import main

helm_binding_exists = True
try:
    from kapitan.inputs.helm.helm_binding import ffi  # this statement will raise ImportError if binding not available
    from kapitan.inputs.helm import render_chart
except ImportError:
    helm_binding_exists = False


@unittest.skipUnless(helm_binding_exists, "helm binding is not available")
class HelmInputTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join("tests", "test_resources"))

    def test_render_chart(self):
        temp_dir = tempfile.mkdtemp()
        chart_path = "charts/acs-engine-autoscaler"
        error_message = render_chart(chart_path, temp_dir)
        self.assertFalse(error_message)
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "secrets.yaml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "deployment.yaml")))

    def test_error_invalid_char_dir(self):
        chart_path = "non-existent"
        temp_dir = tempfile.mkdtemp()
        error_message = render_chart(chart_path, temp_dir)
        self.assertTrue("no such file or directory" in error_message)

    def test_compile_without_helm_values(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "acs-engine-autoscaler"]
        main()
        self.assertTrue(os.path.isfile(
            os.path.join(temp, "compiled", "acs-engine-autoscaler", "chart", "acs", "secrets.yaml")))

    def test_compile_with_helm_values(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "nginx-ingress"]
        main()
        controller_deployment_file = os.path.join(temp, "compiled", "nginx-ingress", "chart", "controller-deployment.yaml")
        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file, 'r') as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest['metadata']['name']
            self.assertEqual(name, '-nginx-ingress-my-controller')

    def test_compile_with_helm_params(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "nginx-ingress-helm-params"]
        with open('inventory/targets/nginx-ingress-helm-params.yml', 'r') as fp:
            manifest = yaml.safe_load(fp.read())
            helm_params = manifest['parameters']['kapitan']['compile'][0]['helm_params']
            release_name = helm_params['release_name']
            namespace = helm_params['namespace']

        main()
        controller_deployment_file = os.path.join(temp, "compiled", "nginx-ingress-helm-params",
                                                  "chart", "controller-deployment.yaml")

        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file, 'r') as fp:
            manifest = yaml.safe_load(fp.read())
            container = manifest['spec']['template']['spec']['containers'][0]
            property = container['args'][4]
            self.assertEqual(property, '--configmap={}/{}'.format(namespace,
                                                                  release_name + '-nginx-ingress-my-controller'))

    def tearDown(self):
        os.chdir('../../')
        reset_cache()
