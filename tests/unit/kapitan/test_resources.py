# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kapitan import cached
from kapitan.errors import CompileError, InventoryError
from kapitan.resources import (
    dir_files_list,
    dir_files_read,
    file_exists,
    generate_inventory,
    get_inventory,
    gzip_b64,
    jinja2_render_file,
    jsonschema_validate,
    read_file,
    resource_callbacks,
    search_imports,
    yaml_dump,
    yaml_dump_stream,
    yaml_load,
    yaml_load_stream,
)
from kapitan.resources import (
    inventory as inventory_func,
)
from kapitan.utils import prune_empty, sha256_string
from tests.support.paths import TESTS_ROOT


def test_resource_callbacks_contains_expected_keys():
    callbacks = resource_callbacks(["/tmp"])
    assert {
        "jinja2_render_file",
        "inventory",
        "file_read",
        "file_exists",
        "dir_files_list",
        "dir_files_read",
        "sha256_string",
        "gzip_b64",
        "yaml_dump",
        "yaml_dump_stream",
        "yaml_load",
        "yaml_load_stream",
        "jsonschema_validate",
    }.issubset(callbacks.keys())


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


def test_read_file_missing_raises(tmp_path):
    with pytest.raises(OSError):
        read_file([str(tmp_path)], "missing.txt")


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


def test_search_imports_reads_from_cache(tmp_path):
    jsonnet_file = tmp_path / "file.jsonnet"
    jsonnet_file.write_text("{a: 1}", encoding="utf-8")

    path, content = search_imports(str(tmp_path), "file.jsonnet", [])
    assert Path(path).name == "file.jsonnet"
    assert content.decode() == "{a: 1}"

    cached_path, cached_content = search_imports(str(tmp_path), "file.jsonnet", [])
    assert cached_path == path
    assert cached_content == content


def test_inventory_missing_path_raises(tmp_path):
    with pytest.raises(InventoryError):
        inventory_func(search_paths=[str(tmp_path)], inventory_path="missing")


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


def test_search_imports_from_search_paths(tmp_path):
    data = tmp_path / "test.jsonnet"
    data.write_text("content", encoding="utf-8")

    path, content = search_imports(
        str(tmp_path / "cwd"), "test.jsonnet", [str(tmp_path)]
    )
    assert path.endswith("test.jsonnet")
    assert content == b"content"


def test_search_imports_from_install_path(monkeypatch, tmp_path):
    install_dir = tmp_path / "kapitan"
    install_dir.mkdir()
    (install_dir / "module.jsonnet").write_text("data", encoding="utf-8")
    monkeypatch.setattr(
        "kapitan.resources.kapitan_install_path",
        str(install_dir / "__init__.py"),
    )

    path, content = search_imports(str(tmp_path / "cwd"), "module.jsonnet", [])
    assert path.endswith("module.jsonnet")
    assert content == b"data"


def test_search_imports_search_paths_fallback(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (second / "fallback.jsonnet").write_text("data", encoding="utf-8")

    path, content = search_imports(
        str(tmp_path / "cwd"), "fallback.jsonnet", [str(first), str(second)]
    )
    assert path.endswith("fallback.jsonnet")
    assert content == b"data"


def test_search_imports_not_found_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        search_imports(str(tmp_path / "cwd"), "missing.jsonnet", [str(tmp_path)])


def test_inventory_function_uses_search_paths(monkeypatch, tmp_path):
    inv = SimpleNamespace(
        get_target=lambda _name: SimpleNamespace(
            model_dump=lambda **_kwargs: {"name": "target"}
        ),
        inventory={"target": {"parameters": {}}},
    )
    monkeypatch.setattr("kapitan.resources.get_inventory", lambda _path: inv)

    inv_path = tmp_path / "inventory"
    inv_path.mkdir()

    result = inventory_func(
        [str(tmp_path)], target_name="target", inventory_path="inventory"
    )
    assert result["name"] == "target"


def test_inventory_function_defaults_search_paths_and_returns_inventory(
    monkeypatch, tmp_path
):
    inv = SimpleNamespace(inventory={"target": {"parameters": {}}})
    monkeypatch.setattr("kapitan.resources.get_inventory", lambda _path: inv)

    inventory_dir = tmp_path / "inventory"
    inventory_dir.mkdir()

    assert inventory_func(inventory_path=str(inventory_dir)) == inv.inventory


def test_jinja2_render_file_success_and_error(tmp_path):
    template = tmp_path / "template.j2"
    template.write_text("hello {{ name }}", encoding="utf-8")
    rendered = jinja2_render_file([str(tmp_path)], "template.j2", '{"name": "kapitan"}')
    assert rendered == "hello kapitan"

    template.write_text("hello {{ missing }}", encoding="utf-8")
    with pytest.raises(CompileError):
        jinja2_render_file([str(tmp_path)], "template.j2", "{}")


def test_generate_inventory_flat_and_pattern(monkeypatch, capsys):
    inv = SimpleNamespace(
        inventory={"target": {"parameters": {"nested": {"value": 1}}}}
    )
    monkeypatch.setattr("kapitan.resources.get_inventory", lambda _path: inv)

    args = _generate_inventory_args(target_name="target", pattern="parameters.nested")

    generate_inventory(args)
    output = capsys.readouterr().out
    assert "value" in output


def test_generate_inventory_flat(monkeypatch, capsys):
    inv = SimpleNamespace(inventory={"target": {"parameters": {"nested": 1}}})
    monkeypatch.setattr("kapitan.resources.get_inventory", lambda _path: inv)

    args = _generate_inventory_args(target_name="target", flat=True)

    generate_inventory(args)
    output = capsys.readouterr().out
    assert "parameters.nested" in output


def test_generate_inventory_no_target(monkeypatch, capsys):
    inv = SimpleNamespace(inventory={"target": {"parameters": {}}})
    monkeypatch.setattr("kapitan.resources.get_inventory", lambda _path: inv)

    args = _generate_inventory_args()

    generate_inventory(args)
    output = capsys.readouterr().out
    assert "parameters" in output


def test_generate_inventory_raises(monkeypatch):
    monkeypatch.setattr(
        "kapitan.resources.get_inventory",
        lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    args = _generate_inventory_args()

    with pytest.raises(RuntimeError):
        generate_inventory(args)


def test_get_inventory_cached_and_migrate(monkeypatch, restore_cached_state):
    cached.inv = SimpleNamespace(targets={"t": object()}, inventory={"t": {}})
    cached.args = SimpleNamespace(
        compose_target_name=False,
        inventory_backend="fake",
        migrate=True,
        compose_node_name=False,
    )

    assert get_inventory("/tmp") is cached.inv

    class _Backend:
        def __init__(self, **_kwargs):
            self.targets = {"t": object()}
            self.inventory = {"t": {}}
            self.migrated = False

        def migrate(self):
            self.migrated = True

    cached.inv = None
    monkeypatch.setattr("kapitan.resources.get_inventory_backend", lambda _id: _Backend)
    inv = get_inventory("/tmp")

    assert inv.inventory == {"t": {}}


def test_get_inventory_compose_node_name_warns(
    monkeypatch, caplog, restore_cached_state
):
    cached.inv = None
    cached.args = SimpleNamespace(
        compose_target_name=False,
        compose_node_name=True,
        inventory_backend="fake",
    )

    class _Backend:
        def __init__(self, **_kwargs):
            self.targets = {"t": object()}
            self.inventory = {"t": {}}

    monkeypatch.setattr("kapitan.resources.get_inventory_backend", lambda _id: _Backend)
    get_inventory("/tmp")

    assert any("compose-node-name" in record.message for record in caplog.records)


def test_get_inventory_backend_error_exits(monkeypatch, restore_cached_state):
    class _Backend:
        def __init__(self, **_kwargs):
            raise InventoryError("boom")

    cached.inv = None
    cached.args = SimpleNamespace(compose_target_name=False, compose_node_name=False)
    monkeypatch.setattr("kapitan.resources.get_inventory_backend", lambda _id: _Backend)

    with pytest.raises(SystemExit):
        get_inventory("/tmp")


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
    result = dir_files_list(search_paths, "resources/fixtures/jsonnet/files")
    expected = ["file1.txt", "file2.txt"]
    assert sorted(result) == sorted(expected)


def test_dir_files_list_missing():
    search_paths = [str(TESTS_ROOT)]
    with pytest.raises(IOError):
        dir_files_list(search_paths, "non_existing_dir")


def test_dir_files_read():
    search_paths = [str(TESTS_ROOT)]
    result = dir_files_read(search_paths, "resources/fixtures/jsonnet/files")
    expected = {
        "file1.txt": "To be, or not to be: that is the question\n",
        "file2.txt": "Nothing will come of nothing.\n",
    }
    assert result == expected


def test_yaml_load_returns_json_for_yaml_document():
    json_output = yaml_load([str(TESTS_ROOT)], "resources/fixtures/yaml/yaml_load.yaml")
    expected_output = """{"test": {"key": "value", "array": ["ele1", "ele2"]}}"""
    assert json_output == expected_output


def test_yaml_load_stream():
    json_output = yaml_load_stream(
        [str(TESTS_ROOT)], "resources/fixtures/yaml/yaml_load_stream.yaml"
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
