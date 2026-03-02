# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from kapitan.utils.data import deep_get, flatten_dict, prune_empty


def test_flatten_dict_and_deep_get():
    nested = {"a": {"b": {"c": 1}}, "x": 2}
    flattened = flatten_dict(nested)
    assert flattened == {"a.b.c": 1, "x": 2}
    assert deep_get(nested, ["a", "b", "c"]) == 1


def test_prune_empty_removes_empty_containers():
    data = {"a": [], "b": {"c": []}, "d": [1, {}, []], "e": 2}
    assert prune_empty(data) == {"b": {}, "d": [1], "e": 2}
    assert prune_empty([]) is None


def test_deep_get_glob_match():
    data = {"FooBar": {"baz": 3}}
    assert deep_get(data, ["*bar", "baz"]) == 3


def test_deep_get_additional_edge_paths():
    assert deep_get({"a": 1}, ["a", "b"]) is None
    assert deep_get({"FooBar": 9}, ["*bar"]) == 9
    assert deep_get({"foo": 1}, ["*bar"]) is None
    assert deep_get({"outer": {"inner": {"needle": "value"}}}, ["needle"]) == "value"
    assert deep_get({"a": 1}, []) is None
    assert deep_get([], ["a"]) is None
