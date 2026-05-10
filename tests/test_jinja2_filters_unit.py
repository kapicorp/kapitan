#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for kapitan.jinja2_filters submodules (FR-009).

Tests cover the new submodule import paths that will exist after the split.
"""

import argparse

from kapitan.jinja2_filters.datetime_filters import strftime, to_datetime
from kapitan.jinja2_filters.encoding import base64_decode, base64_encode
from kapitan.jinja2_filters.regex import (
    regex_escape,
    regex_findall,
    regex_replace,
    regex_search,
)
from kapitan.jinja2_filters.reveal import reveal_maybe
from kapitan.jinja2_filters.serialization import (
    fileglob,
    merge_strategic,
    randomize_list,
    ternary,
    to_bool,
    to_toml,
    to_yaml,
)


class TestEncoding:
    def test_base64_encode(self):
        assert base64_encode("hello") == "aGVsbG8="

    def test_base64_decode(self):
        assert base64_decode("aGVsbG8=") == "hello"

    def test_round_trip(self):
        original = "kapitan rocks"
        assert base64_decode(base64_encode(original)) == original


class TestRegex:
    def test_regex_replace(self):
        assert (
            regex_replace("hello world", pattern="world", replacement="kapitan")
            == "hello kapitan"
        )

    def test_regex_replace_ignorecase(self):
        assert (
            regex_replace(
                "Hello World", pattern="hello", replacement="hi", ignorecase=True
            )
            == "hi World"
        )

    def test_regex_escape(self):
        assert regex_escape("+s[a-z]") == r"\+s\[a\-z\]"

    def test_regex_search_match(self):
        assert regex_search("hello world", r"w\w+") == "world"

    def test_regex_search_no_match(self):
        assert regex_search("hello", r"xyz") is None

    def test_regex_findall(self):
        result = regex_findall("cat bat sat", r"[cbs]at")
        assert result == ["cat", "bat", "sat"]

    def test_regex_findall_multiline(self):
        result = regex_findall("line1\nline2", r"^line\d$", multiline=True)
        assert result == ["line1", "line2"]


class TestDatetimeFilters:
    def test_to_datetime_default_format(self):
        dt = to_datetime("2019-03-07 13:37:00")
        assert dt.year == 2019
        assert dt.month == 3
        assert dt.day == 7

    def test_strftime_with_epoch(self):
        result = strftime("%Y", 0)
        assert result == "1970"

    def test_strftime_without_second_returns_string(self):
        import time

        fmt = "%Y"
        result = strftime(fmt)
        assert result == time.strftime(fmt)


class TestSerialization:
    def test_to_yaml_list(self):
        assert to_yaml(["a", "b"]) == "- a\n- b\n"

    def test_to_yaml_dict(self):
        result = to_yaml({"key": "val"})
        assert "key: val" in result

    def test_to_toml(self):
        result = to_toml({"section": {"key": "val"}})
        assert "[section]" in result

    def test_to_bool_yes(self):
        assert to_bool("yes") is True

    def test_to_bool_false_string(self):
        assert to_bool("false") is False

    def test_to_bool_none(self):
        assert to_bool(None) is None

    def test_to_bool_bool_passthrough(self):
        assert to_bool(True) is True

    def test_ternary_true(self):
        assert ternary(True, "yes", "no") == "yes"

    def test_ternary_false(self):
        assert ternary(False, "yes", "no") == "no"

    def test_ternary_none_val(self):
        assert ternary(None, "yes", "no", "null") == "null"

    def test_randomize_list_with_seed_is_deterministic(self):
        result1 = randomize_list([1, 2, 3, 4, 5], seed=42)
        result2 = randomize_list([1, 2, 3, 4, 5], seed=42)
        assert result1 == result2

    def test_randomize_list_returns_list(self):
        assert isinstance(randomize_list([1, 2, 3]), list)

    def test_fileglob_returns_only_files(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        results = fileglob(str(tmp_path / "*.txt"))
        assert all(map(lambda p: not __import__("os").path.isdir(p), results))


class TestMergeStrategic:
    def test_list_of_dicts_with_name_key_are_merged(self):
        data = [
            {"name": "alice", "role": "admin"},
            {"name": "alice", "extra": "yes"},
            {"name": "bob", "role": "user"},
        ]
        result = merge_strategic(data)
        assert isinstance(result, list)
        alice = next(item for item in result if item["name"] == "alice")
        assert alice.get("extra") == "yes"
        assert alice.get("role") == "admin"

    def test_plain_list_is_unchanged_structure(self):
        data = ["a", "b", "c"]
        result = merge_strategic(data)
        assert result == ["a", "b", "c"]

    def test_non_list_dict_passthrough(self):
        assert merge_strategic("hello") == "hello"
        assert merge_strategic(42) == 42

    def test_nested_dict_is_recursed(self):
        data = {"items": [{"name": "x", "v": 1}, {"name": "x", "v": 2}]}
        result = merge_strategic(data)
        assert "items" in result


class TestReveal:
    def test_reveal_maybe_passthrough_without_reveal_flag(self, reset_cached_args):
        from kapitan import cached

        cached.args = argparse.Namespace(reveal=False)
        result = reveal_maybe("?{base64:some_value}")
        assert result == "?{base64:some_value}"

    def test_reveal_maybe_with_reveal_flag_calls_revealer(self, reset_cached_args):
        from unittest.mock import MagicMock

        from kapitan import cached

        mock_revealer = MagicMock()
        mock_revealer.reveal_raw.return_value = "decoded"
        cached.args = argparse.Namespace(reveal=True)
        cached.revealer_obj = mock_revealer

        result = reveal_maybe("?{base64:some_value}")
        assert result == "decoded"
        mock_revealer.reveal_raw.assert_called_once_with("?{base64:some_value}")
