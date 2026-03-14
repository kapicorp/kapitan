# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from kadet import ABORT_EXCEPTION_TYPE, BaseObj, Dict


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


def test_parse_kwargs():
    kobj = BaseObj.from_dict({"this": "that", "not_hidden": True})
    output = kobj.dump()
    desired_output = {"this": "that", "not_hidden": True}
    assert output == desired_output


def test_dump():
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
    assert output == desired_output


def test_inner():
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
    assert output == desired_output


def test_lists():
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
    assert output == desired_output


def test_need():
    import pytest

    with pytest.raises(ABORT_EXCEPTION_TYPE):
        KadetTestObj(this_should_error=True)


def test_update_root_yaml(tmp_path):
    yaml_file = tmp_path / "input.yml"
    yaml_file.write_text("this: that\nlist: [1,2,3]\n")

    class KadetObjFromYaml(BaseObj):
        def new(self):
            self.root_file(str(yaml_file))

    output = KadetObjFromYaml().dump()
    desired_output = {"this": "that", "list": [1, 2, 3]}
    assert output == desired_output


def test_update_root_json(tmp_path):
    json_file = tmp_path / "input.json"
    json_file.write_text('{"this": "that", "list": [1,2,3]}')

    class KadetObjFromYaml(BaseObj):
        def new(self):
            self.root_file(str(json_file))

    output = KadetObjFromYaml().dump()
    desired_output = {"this": "that", "list": [1, 2, 3]}
    assert output == desired_output


def test_from_json(tmp_path):
    json_file = tmp_path / "input.json"
    json_file.write_text('{"this": "that", "list": [1,2,3]}')

    kobj = BaseObj.from_json(str(json_file))
    output = kobj.dump()
    desired_output = {"this": "that", "list": [1, 2, 3]}
    assert output == desired_output


def test_from_yaml(tmp_path):
    yaml_file = tmp_path / "input.yml"
    yaml_file.write_text("this: that\nlist: [1,2,3]\n")

    kobj = BaseObj.from_yaml(str(yaml_file))
    output = kobj.dump()
    desired_output = {"this": "that", "list": [1, 2, 3]}
    assert output == desired_output
