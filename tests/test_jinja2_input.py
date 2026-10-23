#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for kapitan.inputs.jinja2 — the Jinja2 input compiler."""

import os
import tempfile
import unittest
from argparse import Namespace

import pytest

from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.defaults import DEFAULT_JINJA2_FILTERS_PATH
from kapitan.inputs.jinja2 import Jinja2
from kapitan.inventory.model.input_types import KapitanInputTypeJinja2Config


@pytest.mark.usefixtures("reset_cached_args")
class Jinja2InputTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kapitan_jinja2_test_")
        self.compile_path = os.path.join(self.temp_dir, "compiled")
        os.makedirs(self.compile_path, exist_ok=True)

        # Set up minimal global inventory for the target
        cached.global_inv = {
            "test-target": {
                "parameters": {"kapitan": {"vars": {"my_var": "hello_world"}}}
            }
        }

        # Set up cached args used by Jinja2 compiler
        cached.args = Namespace(
            reveal=False,
            jinja2_filters=DEFAULT_JINJA2_FILTERS_PATH,
            indent=2,
            yaml_use_rapidyaml=False,
            yaml_dump_null_as_empty=False,
        )

        # Set up cached.inv for CompiledFile multiline_string_style lookup
        cached.inv = {"test-target": {"parameters": {}}}

    def tearDown(self):
        reset_cache()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_template(self, name, content):
        path = os.path.join(self.temp_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_compile_single_file(self):
        template_path = self._make_template("test.txt.j2", "{{ my_var }}")

        compiler = Jinja2(
            self.compile_path,
            [self.temp_dir],
            None,
            "test-target",
            cached.args,
        )
        config = KapitanInputTypeJinja2Config(
            input_paths=[template_path],
            output_path=".",
        )
        compiler.compile_file(config, template_path, self.compile_path)

        output_path = os.path.join(self.compile_path, "test.txt.j2")
        self.assertTrue(os.path.exists(output_path))
        with open(output_path) as f:
            self.assertEqual(f.read(), "hello_world")

    def test_compile_directory(self):
        subdir = os.path.join(self.temp_dir, "templates")
        os.makedirs(subdir, exist_ok=True)
        with open(os.path.join(subdir, "a.txt.j2"), "w") as f:
            f.write("A: {{ my_var }}")
        with open(os.path.join(subdir, "b.txt.j2"), "w") as f:
            f.write("B: {{ my_var }}")

        compiler = Jinja2(
            self.compile_path,
            [self.temp_dir],
            None,
            "test-target",
            cached.args,
        )
        config = KapitanInputTypeJinja2Config(
            input_paths=[subdir],
            output_path=".",
        )
        compiler.compile_file(config, subdir, self.compile_path)

        with open(os.path.join(self.compile_path, "a.txt.j2")) as f:
            self.assertEqual(f.read(), "A: hello_world")
        with open(os.path.join(self.compile_path, "b.txt.j2")) as f:
            self.assertEqual(f.read(), "B: hello_world")

    def test_suffix_remove(self):
        template_path = self._make_template("config.txt.j2", "value: {{ my_var }}")

        compiler = Jinja2(
            self.compile_path,
            [self.temp_dir],
            None,
            "test-target",
            cached.args,
        )
        config = KapitanInputTypeJinja2Config(
            input_paths=[template_path],
            output_path=".",
            suffix_remove=True,
            suffix_stripped=".j2",
        )
        compiler.compile_file(config, template_path, self.compile_path)

        # With suffix_remove=True, the output should be "config.txt" not "config.txt.j2"
        output_path = os.path.join(self.compile_path, "config.txt")
        self.assertTrue(os.path.exists(output_path), f"Expected {output_path} to exist")
        with open(output_path) as f:
            self.assertEqual(f.read(), "value: hello_world")

    def test_input_params_injected(self):
        template_path = self._make_template(
            "params.txt.j2", "compile_path: {{ input_params.compile_path }}"
        )

        compiler = Jinja2(
            self.compile_path,
            [self.temp_dir],
            None,
            "test-target",
            cached.args,
        )
        config = KapitanInputTypeJinja2Config(
            input_paths=[template_path],
            output_path=".",
            input_params={"custom_key": "custom_value"},
        )
        compiler.compile_file(config, template_path, self.compile_path)

        output_path = os.path.join(self.compile_path, "params.txt.j2")
        with open(output_path) as f:
            content = f.read()
            self.assertIn("compile_path:", content)
            self.assertIn(self.compile_path, content)

    def test_inventory_context_available(self):
        template_path = self._make_template("inv.txt.j2", "var: {{ my_var }}")

        compiler = Jinja2(
            self.compile_path,
            [self.temp_dir],
            None,
            "test-target",
            cached.args,
        )
        config = KapitanInputTypeJinja2Config(
            input_paths=[template_path],
            output_path=".",
        )
        compiler.compile_file(config, template_path, self.compile_path)

        output_path = os.path.join(self.compile_path, "inv.txt.j2")
        with open(output_path) as f:
            self.assertEqual(f.read(), "var: hello_world")

    def test_compiled_file_permissions_preserved(self):
        template_path = self._make_template("perms.txt.j2", "content")
        # Set a specific mode on the template
        os.chmod(template_path, 0o640)

        compiler = Jinja2(
            self.compile_path,
            [self.temp_dir],
            None,
            "test-target",
            cached.args,
        )
        config = KapitanInputTypeJinja2Config(
            input_paths=[template_path],
            output_path=".",
        )
        compiler.compile_file(config, template_path, self.compile_path)

        output_path = os.path.join(self.compile_path, "perms.txt.j2")
        self.assertTrue(os.path.exists(output_path))
        mode = os.stat(output_path).st_mode & 0o777
        self.assertEqual(mode, 0o640)
