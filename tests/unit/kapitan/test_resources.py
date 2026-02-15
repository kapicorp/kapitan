# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kapitan.errors import CompileError
from kapitan.resources import (
    dir_files_list,
    dir_files_read,
    file_exists,
    gzip_b64,
    jinja2_render_file,
    jsonschema_validate,
    read_file,
    yaml_dump,
    yaml_dump_stream,
    yaml_load,
    yaml_load_stream,
)
from kapitan.utils import prune_empty, sha256_string


def test_jinja2_render_file_missing_raises(tmp_path):
    with pytest.raises(OSError):
        jinja2_render_file([str(tmp_path)], "missing.j2", json.dumps({}))


def test_yaml_load_missing_raises(tmp_path):
    with pytest.raises(OSError):
        yaml_load([str(tmp_path)], "missing.yaml")


def test_yaml_load_invalid_raises(tmp_path):
    yaml_file = tmp_path / "broken.yaml"
    yaml_file.write_text("{:", encoding="utf-8")

    with pytest.raises(CompileError):
        yaml_load([str(tmp_path)], "broken.yaml")


def test_file_exists_false(tmp_path):
    result = file_exists([str(tmp_path)], "missing.txt")
    assert result == {"exists": False, "path": ""}


def test_dir_files_list_missing_raises(tmp_path):
    with pytest.raises(OSError):
        dir_files_list([str(tmp_path)], "missing-dir")


def test_dir_files_read_reads_files(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "one.txt").write_text("one", encoding="utf-8")
    (data_dir / "two.txt").write_text("two", encoding="utf-8")

    result = dir_files_read([str(tmp_path)], "data")
    assert result == {"one.txt": "one", "two.txt": "two"}


def _generate_inventory_args(**overrides):
    base = {
        "inventory_path": "/tmp",
        "target_name": None,
        "pattern": None,
        "flat": False,
        "indent": 2,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_yaml_load_errors_on_invalid_yaml(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(":\n", encoding="utf-8")

    with pytest.raises(CompileError):
        yaml_load([str(tmp_path)], "bad.yaml")

    with pytest.raises(CompileError):
        yaml_load_stream([str(tmp_path)], "bad.yaml")

    with pytest.raises(OSError):
        yaml_load_stream([str(tmp_path)], "missing.yaml")


def test_read_file_and_exists(tmp_path):
    payload = tmp_path / "data.txt"
    payload.write_text("hello", encoding="utf-8")

    assert read_file([str(tmp_path)], "data.txt") == "hello"
    assert file_exists([str(tmp_path)], "data.txt")["exists"] is True
    assert file_exists([str(tmp_path)], "missing.txt")["exists"] is False

    with pytest.raises(OSError):
        read_file([str(tmp_path)], "missing.txt")


def test_dir_files_list_and_read_missing(tmp_path):
    with pytest.raises(OSError):
        dir_files_list([str(tmp_path)], "missing")

    assert dir_files_read([str(tmp_path)], "missing") is None


REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_ROOT = REPO_ROOT / "tests"


def test_yaml_dump_serializes_json_object_to_yaml():
    yaml = yaml_dump('{"key":"value"}')
    assert yaml == "key: value\n"


def test_yaml_dump_stream():
    yaml = yaml_dump_stream('[{"key":"value"},{"key":"value"}]')
    assert yaml == "key: value\n---\nkey: value\n"


def test_file_exists():
    tests_dir = Path(__file__).resolve().parent
    search_paths = [str(tests_dir)]
    result = file_exists(search_paths, "test_resources.py")
    expected = {"exists": True, "path": str(tests_dir / "test_resources.py")}
    assert result == expected


def test_dir_files_list():
    search_paths = [str(TESTS_ROOT)]
    result = dir_files_list(search_paths, "test_jsonnet")
    expected = ["file1.txt", "file2.txt"]
    assert sorted(result) == sorted(expected)


def test_dir_files_list_missing():
    search_paths = [str(TESTS_ROOT)]
    with pytest.raises(IOError):
        dir_files_list(search_paths, "non_existing_dir")


def test_dir_files_read():
    search_paths = [str(TESTS_ROOT)]
    result = dir_files_read(search_paths, "test_jsonnet")
    expected = {
        "file1.txt": "To be, or not to be: that is the question",
        "file2.txt": "Nothing will come of nothing.",
    }
    assert result == expected


def test_yaml_load_returns_json_for_yaml_document():
    json_output = yaml_load([str(TESTS_ROOT)], "test_resources/test_yaml_load.yaml")
    expected_output = """{"test": {"key": "value", "array": ["ele1", "ele2"]}}"""
    assert json_output == expected_output


def test_yaml_load_stream():
    json_output = yaml_load_stream(
        [str(TESTS_ROOT)], "test_resources/test_yaml_load_stream.yaml"
    )
    expected_output = """[{"test1": {"key": "value", "array": ["ele1", "ele2"]}}, {"test2": {"key": "value", "array": ["ele1", "ele2"]}}]"""
    assert json_output == expected_output


def test_sha256_string():
    hash_value = sha256_string("test")
    assert (
        hash_value == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    )


def test_gzip_b64_compresses_and_encodes_text():
    gzip = gzip_b64("test")
    assert gzip == "H4sIAAAAAAAC/ytJLS4BAAx+f9gEAAAA"


def test_prune_empty():
    dictionary = {"hello": "world", "array": [1, 2], "foo": {}, "bar": []}
    pruned = prune_empty(dictionary)
    assert pruned == {"hello": "world", "array": [1, 2]}


def test_jsonschema_valid():
    dictionary = {"msg": "hello, world!", "array": [1, 2]}
    schema = {
        "type": "object",
        "properties": {
            "msg": {"type": "string"},
            "array": {"type": "array", "contains": {"type": "number"}},
        },
    }
    validation = jsonschema_validate(json.dumps(dictionary), json.dumps(schema))

    assert validation["valid"] is True
    assert validation["reason"] == ""


def test_jsonschema_invalid():
    dictionary = {"msg": "hello, world!", "array": ["a", "b", "c"]}
    schema = {
        "type": "object",
        "properties": {
            "msg": {"type": "string"},
            "array": {"type": "array", "contains": {"type": "number"}},
        },
    }
    validation = jsonschema_validate(json.dumps(dictionary), json.dumps(schema))

    assert validation["valid"] is False
    assert validation["reason"] != ""
