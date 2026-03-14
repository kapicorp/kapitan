# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from types import SimpleNamespace

from kapitan import cached
from kapitan.utils.yaml import multiline_str_presenter, null_presenter


class _DummyDumper:
    def represent_scalar(self, tag, data, style=None):
        return {"tag": tag, "data": data, "style": style}


def test_multiline_and_null_presenter_helpers(monkeypatch):
    dumper = _DummyDumper()
    multiline_result = multiline_str_presenter(dumper, "line1\nline2", "literal")
    assert multiline_result["style"] == "|"

    monkeypatch.setattr(cached, "args", SimpleNamespace(yaml_dump_null_as_empty=True))
    empty_null = null_presenter(dumper, None)
    assert empty_null["data"] == ""

    monkeypatch.setattr(cached, "args", SimpleNamespace(yaml_dump_null_as_empty=False))
    default_null = null_presenter(dumper, None)
    assert default_null["data"] == "null"


def test_null_presenter_defaults_when_flag_attribute_is_missing(monkeypatch):
    monkeypatch.setattr(cached, "args", SimpleNamespace())
    result = null_presenter(_DummyDumper(), None)
    assert result["data"] == "null"
