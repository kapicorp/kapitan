#!/usr/bin/env python3
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

"kadet tests"

import tempfile
import unittest
from kapitan.inputs.kadet import BaseObj, Dict


class KadetTestObj(BaseObj):
    def new(self):
        self.need('name', 'Need a name string')
        self.need('size', 'Need a size int')

    def body(self):
        self.root.firstkey = 1
        self.root.nested.firstkey = 2
        self.root['tradicional_key'] = 3
        self.root.withdict = {'A': 'dict'}
        self.root.withbaseobj_init_as = BaseObj(init_as={'init': 'as'})
        bobj = BaseObj()
        bobj.root.inside = "BaseObj"
        self.root.withbaseobj = bobj
        self.root.withDict = Dict({'Another': 'Dict'})


class KadetTestObjWithInner(KadetTestObj):
    def body(self):
        super().body()
        class Inner(BaseObj): # noqa E306
            def body(self):
                self.root.i_am_inside = True
        self.root.inner = Inner()


class KadetTest(unittest.TestCase):
    def test_parse_kwargs(self):
        kobj = BaseObj(this="that", _hidden=True, nothidden=True)
        output = kobj.to_dict()
        desired_output = {"this": "that", "nothidden": True}
        self.assertEqual(output, desired_output)

    def test_to_dict(self):
        kobj = KadetTestObj(name='testObj', size=5)
        output = kobj.to_dict()
        desired_output = {
            "name": "testObj",
            "size": 5,
            "firstkey": 1,
            "tradicional_key": 3,
            "nested": {"firstkey": 2},
            "withdict": {"A": "dict"},
            "withbaseobj_init_as": {"init": "as"},
            "withbaseobj": {"inside": "BaseObj"},
            "withDict": {"Another": "Dict"},
        }
        self.assertEqual(output, desired_output)

    def test_inner(self):
        kobj = KadetTestObjWithInner(name='testWithInnerObj', size=6, _hidden=9)
        output = kobj.to_dict()
        desired_output = {
            "name": "testWithInnerObj",
            "size": 6,
            "firstkey": 1,
            "tradicional_key": 3,
            "nested": {"firstkey": 2},
            "withdict": {"A": "dict"},
            "withbaseobj_init_as": {"init": "as"},
            "withbaseobj": {"inside": "BaseObj"},
            "withDict": {"Another": "Dict"},
            "inner": {"i_am_inside": True},
        }
        self.assertEqual(output, desired_output)

    def test_lists(self):
        kobj = KadetTestObj(name='testObj', size=5)
        kobj.root.withLists = [Dict({"i_am_inside_a_list": True}), BaseObj(init_as={"me": "too"}),
                               BaseObj(list_of_objs=[BaseObj(a=1, b=2), Dict(c=3, d=4)])]
        output = kobj.to_dict()
        desired_output = {
            "name": "testObj",
            "size": 5,
            "firstkey": 1,
            "tradicional_key": 3,
            "nested": {"firstkey": 2},
            "withdict": {"A": "dict"},
            "withbaseobj_init_as": {"init": "as"},
            "withbaseobj": {"inside": "BaseObj"},
            "withDict": {"Another": "Dict"},
            "withLists": [{"i_am_inside_a_list": True}, {"me": "too"},
                          {"list_of_objs": [{"a": 1, "b": 2}, {"c": 3, "d": 4}]}]
        }
        self.assertEqual(output, desired_output)

    def test_need(self):
        with self.assertRaises(Exception):
            KadetTestObj(this_should_error=True)

    def test_root_from_yaml(self):
        yaml_file = tempfile.mktemp()
        with open(yaml_file, 'w') as fp:
            fp.write("this: that\nlist: [1,2,3]\n")

        class KadetObjFromYaml(BaseObj):
            def new(self):
                self.root_from_yaml(yaml_file)

        output = KadetObjFromYaml().to_dict()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)

    def test_root_from_json(self):
        json_file = tempfile.mktemp()
        with open(json_file, 'w') as fp:
            fp.write('{"this": "that", "list": [1,2,3]}')

        class KadetObjFromYaml(BaseObj):
            def new(self):
                self.root_from_json(json_file)

        output = KadetObjFromYaml().to_dict()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)

    def test_from_json(self):
        json_file = tempfile.mktemp()
        with open(json_file, 'w') as fp:
            fp.write('{"this": "that", "list": [1,2,3]}')

        kobj = BaseObj.from_json(json_file)
        output = kobj.to_dict()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)

    def test_from_yaml(self):
        yaml_file = tempfile.mktemp()
        with open(yaml_file, 'w') as fp:
            fp.write("this: that\nlist: [1,2,3]\n")

        kobj = BaseObj.from_yaml(yaml_file)
        output = kobj.to_dict()
        desired_output = {"this": "that", "list": [1, 2, 3]}
        self.assertEqual(output, desired_output)
