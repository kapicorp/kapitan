#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"jinja2 tests"

import base64
import unittest
import tempfile
import time
from kapitan.utils import render_jinja2_file
from kapitan.resources import inventory
from kapitan.inputs.jinja2_filters import base64_encode
from kapitan.refs.base import RefController, Revealer
from kapitan.refs.base64 import Base64Ref
from kapitan import cached
from collections import namedtuple


class Jinja2FiltersTest(unittest.TestCase):
    def test_sha256(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ text|sha256 }}".encode("UTF-8"))
            f.seek(0)
            context = {"text": "this and that"}
            output = "e863c1ac42619a2b429a08775a6acd89ff4c2c6b8dae12e3461a5fa63b2f92f5"
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
            output = "- this\n- that\n"
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

    def test_reveal_maybe_b64encode_tag(self):
        """
        creates ?{base64:some_value} and runs reveal_maybe|b64encode jinja2 filters
        """
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ my_ref_tag_var|reveal_maybe|b64encode }}".encode("UTF-8"))
            f.seek(0)

            # new argparse namespace with --reveal and --refs-path values
            namespace = namedtuple("Namespace", [])
            namespace.reveal = True
            namespace.refs_path = tempfile.mkdtemp()

            # reveal_maybe uses cached, so inject namespace
            cached.args["compile"] = namespace
            cached.ref_controller_obj = RefController(cached.args["compile"].refs_path)
            cached.revealer_obj = Revealer(cached.ref_controller_obj)

            ref_tag = "?{base64:some_value}"
            ref_value = b"sitar_rock!"
            cached.ref_controller_obj[ref_tag] = Base64Ref(ref_value)
            context = {"my_ref_tag_var": ref_tag}
            ref_value_b64 = base64.b64encode(ref_value).decode()
            self.assertEqual(render_jinja2_file(f.name, context), ref_value_b64)

    def test_reveal_maybe_tag_no_reveal_flag(self):
        """
        creates ?{base64:some_value} and runs reveal_maybe jinja2 filters without --reveal flag
        """
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ my_ref_tag_var|reveal_maybe }}".encode("UTF-8"))
            f.seek(0)

            # new argparse namespace with --reveal and --refs-path values
            namespace = namedtuple("Namespace", [])
            namespace.reveal = False
            namespace.refs_path = tempfile.mkdtemp()

            # reveal_maybe uses cached, so inject namespace
            cached.args["compile"] = namespace
            cached.ref_controller_obj = RefController(cached.args["compile"].refs_path)
            cached.revealer_obj = Revealer(cached.ref_controller_obj)

            ref_tag = "?{base64:some_value}"
            ref_value = b"sitar_rock!"
            cached.ref_controller_obj[ref_tag] = Base64Ref(ref_value)
            context = {"my_ref_tag_var": ref_tag}
            self.assertEqual(render_jinja2_file(f.name, context), "?{base64:some_value}")

    def test_reveal_maybe_no_tag(self):
        """
        runs reveal_maybe jinja2 filter on data without ref tags
        """
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{ my_var|reveal_maybe }}".encode("UTF-8"))
            f.seek(0)

            # new argparse namespace with --reveal and --refs-path values
            namespace = namedtuple("Namespace", [])
            namespace.reveal = True
            namespace.refs_path = tempfile.mkdtemp()

            # reveal_maybe uses cached, so inject namespace
            cached.args["compile"] = namespace
            cached.ref_controller_obj = RefController(cached.args["compile"].refs_path)
            cached.revealer_obj = Revealer(cached.ref_controller_obj)

            var_value = "heavy_rock!"
            context = {"my_var": var_value}
            self.assertEqual(render_jinja2_file(f.name, context), var_value)


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
            f.write(
                '{{ inventory_global["%s"].parameters.cluster.name }}'.encode("UTF-8")
                % target_name.encode("UTF-8")
            )
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
            actual_output = render_jinja2_file(
                f.name, context, "./examples/kubernetes/lib/custom_jinja2_filter.py"
            )
            expected_output = base64_encode(cluster_name)
            self.assertEqual(actual_output, expected_output)
