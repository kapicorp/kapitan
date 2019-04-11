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

"jinja2 tests"

import unittest
import tempfile
import time
from kapitan.utils import render_jinja2_file
from kapitan.resources import inventory
from kapitan.inputs.jinja2_filters import base64_encode


class Jinja2FiltersTest(unittest.TestCase):
    def test_sha256(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|sha256 }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "this and that"}
            output = 'e863c1ac42619a2b429a08775a6acd89ff4c2c6b8dae12e3461a5fa63b2f92f5'
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_base64_encode(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|b64encode }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "this and that"}
            output = "dGhpcyBhbmQgdGhhdA=="
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_base64_decode(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|b64decode }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "dGhpcyBhbmQgdGhhdA=="}
            output = "this and that"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_yaml(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|yaml }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": ["this", "that"]}
            output = '- this\n- that\n'
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_fileglob(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|fileglob }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "./tests/*jinja2.py"}
            output = "['./tests/test_jinja2.py']"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_bool(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|bool }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "yes"}
            output = "True"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_to_datetime(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|to_datetime }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "2019-03-07 13:37:00"}
            output = "2019-03-07 13:37:00"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_strftime(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|strftime }}".encode("UTF-8"))
            f.seek(0)
            format = "%a, %d %b %Y %H:%M"
            context = {"text": format}
            output = time.strftime(format)
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_regex_replace(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|regex_replace(pattern='world', replacement='kapitan') }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "hello world"}
            output = "hello kapitan"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_regex_escape(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|regex_escape }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "+s[a-z].*"}
            output = "\\+s\\[a\\-z\\]\\.\\*"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_regex_search(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|regex_search('world.*') }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "hello world"}
            output = "world"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_regex_findall(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|regex_findall('world.*') }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "hello world"}
            output = "['world']"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_ternary(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|ternary('yes', 'no') }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "kapitan == kapitan"}
            output = "yes"
            self.assertEqual(render_jinja2_file(f.name, context), output)

    def test_shuffle(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|shuffle }}".encode("UTF-8"))
            f.seek(0)
            array = [1, 2, 3, 4, 5]
            context = {"text": array}
            self.assertNotEqual(render_jinja2_file(f.name, context), array)


class Jinja2ContextVars(unittest.TestCase):
    def test_inventory_context(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ inventory.parameters.cluster.name }}".encode("UTF-8"))
            cluster_name = "minikube"
            target_name = "minikube-es"
            inv = inventory(["examples/kubernetes"], target_name)
            context = {"inventory": inv}
            f.seek(0)
            self.assertEqual(render_jinja2_file(f.name, context), cluster_name)

    def test_inventory_global_context(self):
        with tempfile.NamedTemporaryFile() as f:
            target_name = "minikube-es"
            f.write("{{ inventory_global[\"%s\"].parameters.cluster.name }}".encode("UTF-8") % target_name.encode("UTF-8"))
            cluster_name = "minikube"
            inv_global = inventory(["examples/kubernetes"], None)
            context = {"inventory_global": inv_global}
            f.seek(0)
            self.assertEqual(render_jinja2_file(f.name, context), cluster_name)


class Jinja2ExternalFilterTest(unittest.TestCase):
    def test_custom_filter_jinja2(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ inventory.parameters.cluster.name | custom_jinja2_filter }}".encode("UTF-8"))
            cluster_name = "minikube"
            target_name = "minikube-es"
            inv = inventory(["examples/kubernetes"], target_name)
            context = {"inventory": inv}
            f.seek(0)
            actual_output = render_jinja2_file(f.name, context, "./examples/kubernetes/lib/custom_jinja2_filter.py")
            expected_output = base64_encode(cluster_name)
            self.assertEqual(actual_output, expected_output)
            
