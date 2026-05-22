#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for kapitan.inputs.base — to_file, CompiledFile, CompilingFile."""

import json
import os
import tempfile
import unittest
from argparse import Namespace

import pytest
import toml
import yaml

from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.errors import CompileError, KapitanError
from kapitan.inputs.base import CompiledFile, InputType
from kapitan.inventory.model.input_types import (
    KapitanInputTypeCopyConfig,
    OutputType,
)


class MockInputType(InputType):
    """Mock InputType for testing base methods."""

    def compile_file(self, config, input_path, compile_path):
        pass

    def inputs_hash(self, *inputs, **kwargs):
        return ""


@pytest.mark.usefixtures("reset_cached_args")
class ToFileTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kapitan_base_test_")
        self.compile_path = os.path.join(self.temp_dir, "compiled")
        os.makedirs(self.compile_path, exist_ok=True)

        cached.args = Namespace(
            reveal=False,
            indent=2,
            yaml_use_rapidyaml=False,
            yaml_dump_null_as_empty=False,
        )
        cached.inv = {"test-target": {"parameters": {}}}

    def tearDown(self):
        reset_cache()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_compiler(self):
        return MockInputType(
            self.compile_path, [self.temp_dir], None, "test-target", cached.args
        )

    def test_to_file_plain(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.PLAIN
        )
        file_path = os.path.join(self.temp_dir, "output")
        compiler.to_file(config, file_path, "hello world")

        self.assertTrue(os.path.exists(file_path))
        with open(file_path) as f:
            self.assertEqual(f.read(), "hello world")

    def test_to_file_json(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.JSON
        )
        file_path = os.path.join(self.temp_dir, "output")
        compiler.to_file(config, file_path, {"key": "value"})

        self.assertTrue(os.path.exists(file_path + ".json"))
        with open(file_path + ".json") as f:
            data = json.load(f)
            self.assertEqual(data["key"], "value")

    def test_to_file_yaml(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.YAML
        )
        file_path = os.path.join(self.temp_dir, "output")
        compiler.to_file(config, file_path, {"key": "value"})

        self.assertTrue(os.path.exists(file_path + ".yaml"))
        with open(file_path + ".yaml") as f:
            data = yaml.safe_load(f)
            self.assertEqual(data["key"], "value")

    def test_to_file_toml(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.TOML
        )
        file_path = os.path.join(self.temp_dir, "output")
        compiler.to_file(config, file_path, {"section": {"key": "value"}})

        self.assertTrue(os.path.exists(file_path + ".toml"))
        with open(file_path + ".toml") as f:
            data = toml.load(f)
            self.assertEqual(data["section"]["key"], "value")

    def test_to_file_auto_detects_json(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.AUTO
        )
        file_path = os.path.join(self.temp_dir, "output.json")
        compiler.to_file(config, file_path, {"key": "value"})

        with open(file_path) as f:
            data = json.load(f)
            self.assertEqual(data["key"], "value")

    def test_to_file_auto_detects_yaml(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.AUTO
        )
        file_path = os.path.join(self.temp_dir, "output.yaml")
        compiler.to_file(config, file_path, {"key": "value"})

        with open(file_path) as f:
            data = yaml.safe_load(f)
            self.assertEqual(data["key"], "value")

    def test_to_file_auto_fallback_to_default(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.AUTO
        )
        file_path = os.path.join(self.temp_dir, "output.unknown")
        compiler.to_file(config, file_path, "plain text")

        # Falls back to YAML (default for MockInputType since it inherits YAML)
        self.assertTrue(os.path.exists(file_path + ".yaml"))

    def test_to_file_prune_empty(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"],
            output_path=".",
            output_type=OutputType.YAML,
            prune=True,
        )
        file_path = os.path.join(self.temp_dir, "output")
        compiler.to_file(
            config, file_path, {"keep": "this", "remove": {}, "also_remove": []}
        )

        with open(file_path + ".yaml") as f:
            data = yaml.safe_load(f)
            self.assertIn("keep", data)
            self.assertNotIn("remove", data)
            self.assertNotIn("also_remove", data)

    def test_to_file_unsupported_output_type(self):
        compiler = self._make_compiler()
        config = KapitanInputTypeCopyConfig(
            input_paths=["dummy"], output_path=".", output_type=OutputType.YAML
        )
        # Force an unsupported output_type after validation to trigger the ValueError
        config.output_type = "UNSUPPORTED"
        file_path = os.path.join(self.temp_dir, "output")

        with self.assertRaises(ValueError) as ctx:
            compiler.to_file(config, file_path, "data")
        self.assertIn("not supported", str(ctx.exception))


@pytest.mark.usefixtures("reset_cached_args")
class CompiledFileTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kapitan_compiled_file_test_")
        cached.args = Namespace(
            reveal=False,
            indent=2,
            yaml_use_rapidyaml=False,
            yaml_dump_null_as_empty=False,
        )
        cached.inv = {"test-target": {"parameters": {}}}

    def tearDown(self):
        reset_cache()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compiled_file_context_manager(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
        with CompiledFile(file_path, None, mode="w", target_name="test-target") as cf:
            cf.write("hello")

        with open(file_path) as f:
            self.assertEqual(f.read(), "hello")

    def test_compiling_file_write_yaml(self):
        file_path = os.path.join(self.temp_dir, "test.yaml")
        with CompiledFile(file_path, None, mode="w", target_name="test-target") as cf:
            cf.write_yaml({"key": "value"})

        with open(file_path) as f:
            data = yaml.safe_load(f)
            self.assertEqual(data["key"], "value")

    def test_compiling_file_write_json(self):
        file_path = os.path.join(self.temp_dir, "test.json")
        with CompiledFile(file_path, None, mode="w", target_name="test-target") as cf:
            cf.write_json({"key": "value"})

        with open(file_path) as f:
            data = json.load(f)
            self.assertEqual(data["key"], "value")

    def test_compiling_file_write_toml(self):
        file_path = os.path.join(self.temp_dir, "test.toml")
        with CompiledFile(file_path, None, mode="w", target_name="test-target") as cf:
            cf.write_toml({"section": {"key": "value"}})

        with open(file_path) as f:
            data = toml.load(f)
            self.assertEqual(data["section"]["key"], "value")

    def test_compiling_file_skips_empty_yaml(self):
        file_path = os.path.join(self.temp_dir, "test.yaml")
        with CompiledFile(file_path, None, mode="w", target_name="test-target") as cf:
            cf.write_yaml({})

        # Empty YAML should be skipped (file created but empty)
        self.assertTrue(os.path.exists(file_path))

    def test_compile_input_path_wraps_kapitan_error(self):
        class FailingInputType(InputType):
            def compile_file(self, config, input_path, compile_path):
                raise KapitanError("simulated failure")

            def inputs_hash(self, *inputs, **kwargs):
                return ""

        compile_path = os.path.join(self.temp_dir, "compiled")
        os.makedirs(compile_path, exist_ok=True)
        compiler = FailingInputType(compile_path, [], None, "test-target", cached.args)
        config = KapitanInputTypeCopyConfig(input_paths=["dummy"], output_path=".")

        with self.assertRaises(CompileError) as ctx:
            compiler.compile_input_path(config, "/some/path")
        self.assertIn("test-target", str(ctx.exception))
        self.assertIn("simulated failure", str(ctx.exception))
