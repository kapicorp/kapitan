#!/usr/bin/env python3

import builtins
from types import SimpleNamespace

import jinja2
import pytest

import kapitan.utils  # noqa: F401
from kapitan import cached, defaults
from kapitan.errors import CompileError
from kapitan.jinja2_filters import (
    _jinja_error_info,
    base64_decode,
    base64_encode,
    fileglob,
    load_jinja2_filters,
    load_jinja2_filters_from_file,
    load_module_from_path,
    merge_strategic,
    randomize_list,
    regex_escape,
    regex_findall,
    regex_replace,
    regex_search,
    reveal_maybe,
    strftime,
    ternary,
    to_bool,
    to_datetime,
    to_toml,
    to_yaml,
)


def test_load_jinja2_filters_registers_expected():
    env = jinja2.Environment()
    load_jinja2_filters(env)
    for key in (
        "sha256",
        "b64encode",
        "b64decode",
        "yaml",
        "toml",
        "fileglob",
        "bool",
        "regex_replace",
        "regex_escape",
        "regex_search",
        "regex_findall",
        "reveal_maybe",
        "ternary",
        "shuffle",
        "merge_strategic",
    ):
        assert key in env.filters


def test_load_module_from_path_registers_filter(tmp_path):
    module_path = tmp_path / "filters.py"
    module_path.write_text(
        "def custom_filter(value):\n    return value + '!'\n",
        encoding="utf-8",
    )

    env = jinja2.Environment()
    load_module_from_path(env, str(module_path))
    assert env.filters["custom_filter"]("ok") == "ok!"


def test_load_jinja2_filters_from_file_default_missing(tmp_path, monkeypatch):
    env = jinja2.Environment()
    missing_path = tmp_path / "missing_filters.py"
    monkeypatch.setattr(defaults, "DEFAULT_JINJA2_FILTERS_PATH", str(missing_path))
    load_jinja2_filters_from_file(env, defaults.DEFAULT_JINJA2_FILTERS_PATH)


def test_regex_search_with_groups():
    result = regex_search("hello123", r"(hello)(\d+)", "\\1", "\\2")
    assert result == ["hello", "123"]


def test_regex_search_unknown_arg():
    with pytest.raises(CompileError):
        regex_search("hello", "hello", "bad")


def test_strftime_invalid_epoch():
    with pytest.raises(CompileError):
        strftime("%Y", second="bad")


def test_to_bool_cases():
    assert to_bool(None) is None
    assert to_bool(True) is True
    assert to_bool("YES") is True
    assert to_bool("no") is False


def test_randomize_list_seeded():
    values = [1, 2, 3, 4]
    shuffled = randomize_list(values, seed=1)
    assert shuffled != values
    assert sorted(shuffled) == sorted(values)


def test_merge_strategic_merges_by_name():
    data = [
        {"name": "app", "replicas": 1},
        {"name": "app", "image": "nginx"},
    ]
    assert merge_strategic(data) == [{"name": "app", "replicas": 1, "image": "nginx"}]


def test_jinja_error_info_and_module_load_error_paths(tmp_path):
    assert _jinja_error_info([("file.py", 1, "other", "line")]) is None

    broken_module = tmp_path / "broken_filters.py"
    broken_module.write_text("def bad(:\n    pass\n", encoding="utf-8")
    env = jinja2.Environment()
    with pytest.raises(OSError):
        load_module_from_path(env, str(broken_module))


def test_load_jinja2_filters_from_default_path_when_file_exists(tmp_path, monkeypatch):
    filter_file = tmp_path / "jinja2_filters.py"
    filter_file.write_text(
        "def custom_default_filter(value):\n    return value + '-ok'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(defaults, "DEFAULT_JINJA2_FILTERS_PATH", str(filter_file))

    env = jinja2.Environment()
    load_jinja2_filters_from_file(env, defaults.DEFAULT_JINJA2_FILTERS_PATH)
    assert env.filters["custom_default_filter"]("value") == "value-ok"


def test_load_jinja2_filters_from_custom_path(tmp_path):
    filter_file = tmp_path / "custom_filters.py"
    filter_file.write_text(
        "def custom_custom_filter(value):\n    return value + '-custom'\n",
        encoding="utf-8",
    )

    env = jinja2.Environment()
    load_jinja2_filters_from_file(env, str(filter_file))
    assert env.filters["custom_custom_filter"]("value") == "value-custom"


def test_regex_helpers_cover_additional_flags_and_no_match_paths():
    assert regex_replace("Alpha", "alpha", "beta", ignorecase=True) == "beta"
    assert regex_search(
        "Line1\nLine2",
        r"line(?P<num>\d)",
        "\\g<num>",
        ignorecase=True,
    ) == ["1"]
    assert regex_search("nomatch", r"line(\d)") is None
    assert regex_findall("A\nB", r"^.", multiline=True, ignorecase=True) == ["A", "B"]


def test_ternary_randomize_and_merge_strategic_additional_paths():
    assert ternary(None, "true", "false", none_val="none") == "none"
    assert ternary("", "true", "false") == "false"
    assert randomize_list(123) == 123

    assert merge_strategic([{"a": 1}, {"b": 2}]) == [{"a": 1}, {"b": 2}]
    assert merge_strategic({"items": [{"a": 1}]}) == {"items": [{"a": 1}]}


def test_to_bool_integer_and_regex_search_multiline_flag():
    assert to_bool(1) is True
    assert regex_search("line1\nline2", r"^line2$", multiline=True) == "line2"


def test_merge_strategic_reaches_dict_guard_false_fallthrough(monkeypatch):
    sentinel = object()
    real_isinstance = builtins.isinstance

    def _patched_isinstance(obj, cls):
        if obj is sentinel and cls == (list | dict):
            return True
        if obj is sentinel and cls in (list, dict):
            return False
        return real_isinstance(obj, cls)

    monkeypatch.setattr("builtins.isinstance", _patched_isinstance)
    assert merge_strategic(sentinel) is None


def test_basic_filters_cover_remaining_paths(tmp_path, monkeypatch):
    marker = tmp_path / "match.txt"
    marker.write_text("hello", encoding="utf-8")

    previous_args = cached.args
    previous_revealer = cached.revealer_obj
    try:
        cached.args = SimpleNamespace(reveal=True)
        cached.revealer_obj = SimpleNamespace(
            reveal_raw=lambda ref_tag: f"revealed:{ref_tag}"
        )
        assert reveal_maybe("?{plain:test}") == "revealed:?{plain:test}"

        cached.args = SimpleNamespace(reveal=False)
        assert reveal_maybe("?{plain:test}") == "?{plain:test}"
    finally:
        cached.args = previous_args
        cached.revealer_obj = previous_revealer

    assert base64_encode("hello") == "aGVsbG8="
    assert base64_decode("aGVsbG8=") == "hello"
    assert to_yaml({"value": 1}) == "value: 1\n"
    assert to_toml({"section": {"value": "ok"}}) == '[section]\nvalue = "ok"\n'
    assert fileglob(str(tmp_path / "*.txt")) == [str(marker)]
    assert to_datetime("2024-01-02 03:04:05").year == 2024
    assert strftime("%Y")
    assert strftime("%Y", second=0) == "1970"
    assert regex_replace("abc", "b", "x") == "axc"
    assert regex_escape("a+b") == "a\\+b"
    assert regex_findall("Ab", "a.") == []
    assert ternary("value", "true", "false") == "true"

    monkeypatch.setattr(
        "kapitan.jinja2_filters.shuffle", lambda values: values.reverse()
    )
    assert randomize_list([1, 2, 3]) == [3, 2, 1]
