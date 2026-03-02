# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import sys
import types
from pathlib import Path

import yaml

import kapitan.utils.compat as compat_module


def test_compat_module_falls_back_to_strenum_and_yaml_safeloader(monkeypatch):
    import enum as real_enum

    import yaml as real_yaml

    class _FakeStrEnum(str):
        __slots__ = ()

    fake_enum = types.ModuleType("enum")
    for attr in dir(real_enum):
        if attr == "StrEnum":
            continue
        setattr(fake_enum, attr, getattr(real_enum, attr))

    fake_strenum = types.ModuleType("strenum")
    fake_strenum.StrEnum = _FakeStrEnum

    fake_yaml = types.ModuleType("yaml")
    for attr in dir(real_yaml):
        if attr == "CSafeLoader":
            continue
        setattr(fake_yaml, attr, getattr(real_yaml, attr))

    module_path = Path(compat_module.__file__)
    temp_module_name = "kapitan.utils.compat_test_import_fallbacks"

    monkeypatch.setitem(sys.modules, "enum", fake_enum)
    monkeypatch.setitem(sys.modules, "strenum", fake_strenum)
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)
    monkeypatch.delitem(sys.modules, temp_module_name, raising=False)

    spec = importlib.util.spec_from_file_location(temp_module_name, module_path)
    temp_module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(temp_module)

    assert temp_module.StrEnum is _FakeStrEnum
    assert temp_module.YamlLoader is yaml.SafeLoader
