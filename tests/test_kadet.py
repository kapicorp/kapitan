#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"kadet tests"

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import kadet
from kadet import BaseObj, Dict

from kapitan.inputs.kadet import Kadet
from kapitan.inventory.model.input_types import KapitanInputTypeKadetConfig


class KadetTestObj(BaseObj):
    def new(self):
        self.need("name", "Need a name string")
        self.need("size", "Need a size int")

    def body(self):
        self.root.name = self.kwargs.name
        self.root.size = self.kwargs.size
        self.root.first_key = 1
        self.root.nested.first_key = 2
        self.root["traditional_key"] = 3
        self.root.with_dict = {"A": "dict"}
        self.root.with_baseobj_init_as = BaseObj.from_dict({"init": "as"})
        bobj = BaseObj()
        bobj.root.inside = "BaseObj"
        self.root.with_baseobj = bobj
        self.root.with_another_dict = Dict({"Another": "Dict"})


class KadetTestObjWithInner(KadetTestObj):
    def body(self):
        super().body()

        class Inner(BaseObj):
            def body(self):
                self.root.i_am_inside = True

        self.root.inner = Inner()


class KadetTest(unittest.TestCase):
    def test_parse_kwargs(self):
        kobj = BaseObj.from_dict({"this": "that", "not_hidden": True})
        output = kobj.dump()
        desired_output = {"this": "that", "not_hidden": True}
        self.assertEqual(output, desired_output)

    def test_dump(self):
        kobj = KadetTestObj(name="testObj", size=5)
        output = kobj.dump()
        desired_output = {
            "name": "testObj",
            "size": 5,
            "first_key": 1,
            "traditional_key": 3,
            "nested": {"first_key": 2},
            "with_dict": {"A": "dict"},
            "with_baseobj_init_as": {"init": "as"},
            "with_baseobj": {"inside": "BaseObj"},
            "with_another_dict": {"Another": "Dict"},
        }
        self.assertEqual(output, desired_output)

    def test_inner(self):
        kobj = KadetTestObjWithInner(name="testWithInnerObj", size=6)
        output = kobj.dump()
        desired_output = {
            "name": "testWithInnerObj",
            "size": 6,
            "first_key": 1,
            "traditional_key": 3,
            "nested": {"first_key": 2},
            "with_dict": {"A": "dict"},
            "with_baseobj_init_as": {"init": "as"},
            "with_baseobj": {"inside": "BaseObj"},
            "with_another_dict": {"Another": "Dict"},
            "inner": {"i_am_inside": True},
        }
        self.assertEqual(output, desired_output)

    def test_lists(self):
        kobj = KadetTestObj(name="testObj", size=5)
        kobj.root.with_lists = [
            Dict({"i_am_inside_a_list": True}),
            BaseObj.from_dict({"me": "too"}),
            BaseObj.from_dict(
                {
                    "list_of_objs": [
                        BaseObj.from_dict(dict(a=1, b=2)),
                        Dict(dict(c=3, d=4)),
                    ]
                }
            ),
        ]
        output = kobj.dump()
        desired_output = {
            "name": "testObj",
            "size": 5,
            "first_key": 1,
            "traditional_key": 3,
            "nested": {"first_key": 2},
            "with_dict": {"A": "dict"},
            "with_baseobj_init_as": {"init": "as"},
            "with_baseobj": {"inside": "BaseObj"},
            "with_another_dict": {"Another": "Dict"},
            "with_lists": [
                {"i_am_inside_a_list": True},
                {"me": "too"},
                {"list_of_objs": [{"a": 1, "b": 2}, {"c": 3, "d": 4}]},
            ],
        }
        self.assertEqual(output, desired_output)

    def test_need(self):
        with self.assertRaises(kadet.ABORT_EXCEPTION_TYPE):
            KadetTestObj(this_should_error=True)

    def test_update_root_yaml(self):
        yaml_file = tempfile.mktemp(suffix=".yml")
        with open(yaml_file, "w") as fp:
            fp.write("this: that\nlist: [1,2,3]\n")

        class KadetObjFromYaml(BaseObj):
            def new(self):
                self.root_file(yaml_file)

        output = KadetObjFromYaml().dump()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)

    def test_update_root_json(self):
        json_file = tempfile.mktemp(suffix=".json")
        with open(json_file, "w") as fp:
            fp.write('{"this": "that", "list": [1,2,3]}')

        class KadetObjFromYaml(BaseObj):
            def new(self):
                self.root_file(json_file)

        output = KadetObjFromYaml().dump()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)

    def test_from_json(self):
        json_file = tempfile.mktemp()
        with open(json_file, "w") as fp:
            fp.write('{"this": "that", "list": [1,2,3]}')

        kobj = BaseObj.from_json(json_file)
        output = kobj.dump()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)

    def test_from_yaml(self):
        yaml_file = tempfile.mktemp()
        with open(yaml_file, "w") as fp:
            fp.write("this: that\nlist: [1,2,3]\n")

        kobj = BaseObj.from_yaml(yaml_file)
        output = kobj.dump()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)


class KadetCacheKeyTest(unittest.TestCase):
    """
    Regression tests for PR-1520: compile_path must not be included in the
    cache key because it is a per-run temporary directory that changes on every
    invocation, which would cause every cache lookup to miss.
    """

    def _make_compiler(self):
        compiler = Kadet.__new__(Kadet)
        compiler.target_name = "test-target"
        compiler.search_paths = []
        return compiler

    def test_compile_path_excluded_from_cache_key(self):
        """inputs_hash must be called without compile_path so that volatile
        tempdir paths do not prevent cache hits across runs."""
        compiler = self._make_compiler()

        config = KapitanInputTypeKadetConfig(
            input_paths=["component"],
            output_path=".",
            input_params={"value": "first"},
        )

        cache_obj = mock.Mock()
        cache_obj.get.return_value = {"output.yml": {"key": "val"}}

        with (
            mock.patch.object(compiler, "cacheable", return_value=cache_obj),
            mock.patch.object(
                compiler, "inputs_hash", return_value="fixed-hash"
            ) as mock_hash,
            mock.patch(
                "kapitan.inputs.kadet.inventory_digest", return_value=b"inventory"
            ),
            mock.patch.object(compiler, "to_file"),
        ):
            compiler.compile_file(
                config, "component", "/tmp/run1-abc/compiled/test-target"
            )

        mock_hash.assert_called_once_with(
            b"inventory",
            "test-target",
            Path("component"),
            {"value": "first"},  # compile_path must NOT be present in the hash
        )

    def test_different_compile_paths_yield_same_hash_args(self):
        """Two invocations with different compile_path values must produce
        identical inputs_hash arguments so the second call gets a cache hit."""
        compiler = self._make_compiler()

        config = KapitanInputTypeKadetConfig(
            input_paths=["component"],
            output_path=".",
            input_params={"value": "second"},
        )

        cache_obj = mock.Mock()
        cache_obj.get.return_value = {"output.yml": {"k": "v"}}

        calls = []

        def capture_hash(*args):
            calls.append(args)
            return "stable-hash"

        with (
            mock.patch.object(compiler, "cacheable", return_value=cache_obj),
            mock.patch.object(compiler, "inputs_hash", side_effect=capture_hash),
            mock.patch("kapitan.inputs.kadet.inventory_digest", return_value=b"inv"),
            mock.patch.object(compiler, "to_file"),
        ):
            compiler.compile_file(
                config, "component", "/tmp/run1-xyz/compiled/test-target"
            )
            compiler.compile_file(
                config, "component", "/tmp/run2-qrs/compiled/test-target"
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(
            calls[0],
            calls[1],
            "Cache key must be stable across different compile_paths",
        )

    def test_config_input_params_not_mutated(self):
        """compile_file must not mutate config.input_params (compile_path is injected
        into a local copy only)."""
        compiler = self._make_compiler()

        original_params = {"value": "third"}
        config = KapitanInputTypeKadetConfig(
            input_paths=["component"],
            output_path=".",
            input_params=dict(original_params),
        )

        cache_obj = mock.Mock()
        cache_obj.get.return_value = {"output.yml": {"k": "v"}}

        with (
            mock.patch.object(compiler, "cacheable", return_value=cache_obj),
            mock.patch.object(compiler, "inputs_hash", return_value="hash"),
            mock.patch("kapitan.inputs.kadet.inventory_digest", return_value=b"inv"),
            mock.patch.object(compiler, "to_file"),
        ):
            compiler.compile_file(config, "component", "compiled/test-target")

        self.assertEqual(dict(config.input_params), original_params)

    def test_helm_deps_digest_mixed_into_cache_key(self):
        """When a target declares helm dependencies, the resulting digest must
        be passed into inputs_hash so that chart edits invalidate the kadet
        cache."""
        compiler = self._make_compiler()

        config = KapitanInputTypeKadetConfig(
            input_paths=["component"],
            output_path=".",
            input_params={},
        )

        cache_obj = mock.Mock()
        cache_obj.get.return_value = {"output.yml": {"k": "v"}}

        with (
            mock.patch.object(compiler, "cacheable", return_value=cache_obj),
            mock.patch.object(
                compiler, "inputs_hash", return_value="hash"
            ) as mock_hash,
            mock.patch("kapitan.inputs.kadet.inventory_digest", return_value=b"inv"),
            mock.patch(
                "kapitan.inputs.kadet.helm_dependencies_digest",
                return_value=b"helm-deps-digest",
            ),
            mock.patch(
                "kapitan.inputs.kadet.consumed_topics_digest", return_value=None
            ),
            mock.patch.object(compiler, "to_file"),
        ):
            compiler.compile_file(config, "component", "compiled/test-target")

        args = mock_hash.call_args.args
        self.assertIn(b"helm-deps-digest", args)

    def test_no_helm_deps_means_no_extra_input(self):
        """Targets without helm deps must keep their pre-existing cache key shape."""
        compiler = self._make_compiler()

        config = KapitanInputTypeKadetConfig(
            input_paths=["component"],
            output_path=".",
            input_params={},
        )

        cache_obj = mock.Mock()
        cache_obj.get.return_value = {"output.yml": {"k": "v"}}

        with (
            mock.patch.object(compiler, "cacheable", return_value=cache_obj),
            mock.patch.object(
                compiler, "inputs_hash", return_value="hash"
            ) as mock_hash,
            mock.patch("kapitan.inputs.kadet.inventory_digest", return_value=b"inv"),
            mock.patch(
                "kapitan.inputs.kadet.helm_dependencies_digest", return_value=None
            ),
            mock.patch(
                "kapitan.inputs.kadet.consumed_topics_digest", return_value=None
            ),
            mock.patch.object(compiler, "to_file"),
        ):
            compiler.compile_file(config, "component", "compiled/test-target")

        mock_hash.assert_called_once_with(
            b"inv",
            "test-target",
            Path("component"),
            {},
        )
