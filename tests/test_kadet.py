#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"kadet tests"

import tempfile
import unittest
from argparse import Namespace
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


class KadetCompileCacheTest(unittest.TestCase):
    def test_compile_cache_key_includes_input_params(self):
        input_params = {"value": "second"}
        config = KapitanInputTypeKadetConfig(
            input_paths=["component"],
            output_path=".",
            input_params=input_params,
        )
        compiler = Kadet(
            "compiled",
            ["."],
            None,
            "test-target",
            Namespace(cache=True),
        )

        cache = mock.Mock()
        cache.get.return_value = {}

        with (
            mock.patch.object(compiler, "cacheable", return_value=cache),
            mock.patch.object(
                compiler, "inputs_hash", return_value="cache-key"
            ) as inputs_hash,
            mock.patch(
                "kapitan.inputs.kadet.inventory_digest", return_value=b"inventory"
            ),
        ):
            compiler.compile_file(config, "component", "compiled/test-target")

        inputs_hash.assert_called_once_with(
            b"inventory",
            "test-target",
            Path("component"),
            {"value": "second", "compile_path": "compiled/test-target"},
        )
        cache.get.assert_called_once_with("cache-key")
        self.assertEqual(config.input_params, input_params)
