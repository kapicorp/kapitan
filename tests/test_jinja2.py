#!/usr/bin/env python3.6
#
# Copyright 2018 The Kapitan Authors
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

"jinja2 tests"

import unittest
import tempfile
from kapitan.utils import render_jinja2_file
from kapitan.resources import inventory


class Jinja2FiltersTest(unittest.TestCase):
    def test_sha256(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{text|sha256}}".encode("UTF-8"))
            f.seek(0)
            context = {"text":"this and that"}
            digest = 'e863c1ac42619a2b429a08775a6acd89ff4c2c6b8dae12e3461a5fa63b2f92f5'
            self.assertEqual(render_jinja2_file(f.name, context), digest)

    def test_yaml(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{text|yaml}}".encode("UTF-8"))
            f.seek(0)
            context = {"text":["this", "that"]}
            yaml = '- this\n- that\n'
            self.assertEqual(render_jinja2_file(f.name, context), yaml)


class Jinja2ContextVars(unittest.TestCase):
    def test_inventory_context(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{inventory.parameters.cluster.name}}".encode("UTF-8"))
            cluster_name = "minikube"
            target_name = "minikube-es"
            inv = inventory(["examples/kubernetes"], target_name)
            context = {"inventory": inv}
            f.seek(0)
            self.assertEqual(render_jinja2_file(f.name, context), cluster_name)

    def test_inventory_global_context(self):
        with tempfile.NamedTemporaryFile() as f:
            target_name = "minikube-es"
            f.write("{{inventory_global[\"%s\"].parameters.cluster.name}}".encode("UTF-8") % target_name.encode("UTF-8"))
            cluster_name = "minikube"
            inv_global = inventory(["examples/kubernetes"], None)
            context = {"inventory_global": inv_global}
            f.seek(0)
            self.assertEqual(render_jinja2_file(f.name, context), cluster_name)
