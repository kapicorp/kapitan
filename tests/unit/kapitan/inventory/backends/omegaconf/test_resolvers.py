#!/usr/bin/env python3

import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from kapitan.inventory.backends.omegaconf import resolvers


def test_access_key_with_dots():
    root = OmegaConf.create({"a.b": {"c": 1}})
    assert resolvers.access_key_with_dots("a.b", "c", _root_=root) == 1


def test_escape_interpolation():
    assert resolvers.escape_interpolation("foo.bar") == "${foo.bar}"


def test_to_dict_and_to_list():
    input_list = [{"a": 1}, {"b": 2}]
    assert resolvers.to_dict(input_list) == input_list
    assert resolvers.to_list({"a": 1, "b": 2}) == [{"a": 1}, {"b": 2}]


def test_to_yaml_resolver_serializes_selected_key():
    root = OmegaConf.create({"a": {"b": 1}})
    output = resolvers.to_yaml("a", _root_=root)
    assert "b: 1" in output


def test_default_resolver_builds_nested_oc_select():
    value = resolvers.default("foo.bar", "baz", "fallback")
    assert value == "${oc.select:foo.bar,${oc.select:baz,fallback}}"


def test_relpath_self_reference():
    root = OmegaConf.create({"a": {"b": {"c": 1}}})
    node = root._get_node("a")._get_node("b")._get_node("c")
    assert resolvers.relpath("a.b.c", node) == "SELF REFERENCE DETECTED"


def test_relpath_diverges():
    root = OmegaConf.create({"a": {"b": {"c": 1}}})
    node = root._get_node("a")._get_node("b")._get_node("c")
    assert resolvers.relpath("a.x", node) == "${..x}"


def test_write_to_key(tmp_path, monkeypatch):
    root = OmegaConf.create({"source": {"value": 1}})
    original_resolve = resolvers.OmegaConf.resolve
    original_set_readonly = resolvers.OmegaConf.set_readonly

    def _resolve_compat(config, *_args, **_kwargs):
        return original_resolve(config)

    def _set_readonly_compat(config, flag, **_kwargs):
        return original_set_readonly(config, flag)

    monkeypatch.setattr(resolvers.OmegaConf, "resolve", _resolve_compat)
    monkeypatch.setattr(resolvers.OmegaConf, "set_readonly", _set_readonly_compat)

    assert resolvers.write_to_key("dest", "source", root) == "DONE"
    assert OmegaConf.select(root, "dest.value") == 1

    assert resolvers.write_to_key("missing", "not.there", root) == "NOT FOUND"


def test_from_file_resolver_reads_existing_or_missing_file(tmp_path):
    file_path = tmp_path / "data.txt"
    file_path.write_text("hello", encoding="utf-8")
    assert resolvers.from_file(str(file_path)) == "hello"
    assert resolvers.from_file(str(Path(tmp_path / "missing.txt"))) == "FILE NOT EXISTS"


def test_conditions():
    assert resolvers.condition_if("yes", {"a": 1}) == {"a": 1}
    assert resolvers.condition_if("", {"a": 1}) == {}
    assert resolvers.condition_if_else("yes", {"a": 1}, {"b": 2}) == {"a": 1}
    assert resolvers.condition_if_else("", {"a": 1}, {"b": 2}) == {"b": 2}
    assert resolvers.condition_not("") is True
    assert resolvers.condition_and(True, True, False) is False
    assert resolvers.condition_or(False, False, True) is True
    assert resolvers.condition_equal(1, 1, 1) is True
    assert resolvers.condition_equal(1, 2) is False


def test_key_parentkey_fullkey_and_merge_helpers():
    root = OmegaConf.create({"a": {"b": 1}, "items": [1]})
    node_a = root._get_node("a")
    node_b = node_a._get_node("b")

    assert resolvers.key(node_b) == "b"
    assert resolvers.parentkey(node_b._get_parent()) == "a"
    assert resolvers.fullkey(node_b) == "a.b"

    merged = resolvers.merge(
        OmegaConf.create({"items": [1]}),
        OmegaConf.create({"items": [2]}),
    )
    assert OmegaConf.to_container(merged, resolve=True) == {"items": [1, 2]}


def test_to_dict_and_to_list_additional_paths():
    item_a = OmegaConf.create({"a": 1})
    item_b = OmegaConf.create({"b": 2})

    assert resolvers.to_dict([item_a, item_b]) == {"a": 1, "b": 2}
    assert resolvers.to_dict(("not", "a", "list")) == ("not", "a", "list")
    assert resolvers.to_list(("x", "y")) == ["x", "y"]


def test_write_to_key_returns_error_while_resolving(monkeypatch):
    root = OmegaConf.create({"source": {"value": 1}})

    def _raise_resolve(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(resolvers.OmegaConf, "resolve", _raise_resolve)
    assert resolvers.write_to_key("dest", "source", root) == "ERROR WHILE RESOLVING"


def test_write_to_key_reraises_outer_exception(monkeypatch):
    root = OmegaConf.create({"source": {"value": 1}})

    def _raise_select(*_args, **_kwargs):
        raise ValueError("select failed")

    monkeypatch.setattr(resolvers.OmegaConf, "select", _raise_select)

    with pytest.raises(ValueError, match="select failed"):
        resolvers.write_to_key("dest", "source", root)


def test_filename_parent_filename_path_parent_path_helpers():
    class _NodeWithFlags:
        def __init__(self, values):
            self._values = values

        def _get_flag(self, key):
            return self._values[key]

    node = _NodeWithFlags({"filename": "a.yml", "path": "inventory/targets/a.yml"})

    assert resolvers.filename(node) == "a.yml"
    assert resolvers.parent_filename(node) == "a.yml"
    assert resolvers.path(node) == "inventory/targets/a.yml"
    assert resolvers.parent_path(node) == "inventory/targets/a.yml"


def test_register_resolvers_handles_user_resolver_import_failure(monkeypatch):
    monkeypatch.setattr(resolvers.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(
        resolvers,
        "register_user_resolvers",
        lambda _p: (_ for _ in ()).throw(RuntimeError("bad resolver file")),
    )

    # Should not raise even if user resolver import fails.
    resolvers.register_resolvers()


def test_register_resolvers_imports_existing_user_resolver_file(monkeypatch):
    called = []

    monkeypatch.setattr(resolvers.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(
        resolvers,
        "register_user_resolvers",
        lambda path: called.append(path),
    )

    resolvers.register_resolvers()

    assert called


def test_register_resolvers_skips_missing_user_resolver_file(monkeypatch):
    monkeypatch.setattr(resolvers.os.path, "exists", lambda _p: False)
    monkeypatch.setattr(
        resolvers,
        "register_user_resolvers",
        lambda _p: (_ for _ in ()).throw(
            AssertionError("user resolvers should not be loaded")
        ),
    )

    resolvers.register_resolvers()


def test_register_user_resolvers_missing_file_logs_and_returns(monkeypatch):
    monkeypatch.setattr(resolvers.os.path, "exists", lambda _p: False)
    resolvers.register_user_resolvers("/tmp/does-not-exist/resolvers.py")


def test_register_user_resolvers_handles_missing_pass_resolvers(tmp_path, monkeypatch):
    resolver_file = tmp_path / "resolvers.py"
    resolver_file.write_text("x = 1\n", encoding="utf-8")
    sys.modules.pop("resolvers", None)
    monkeypatch.setattr(resolvers.sys, "path", [str(tmp_path), *resolvers.sys.path])

    resolvers.register_user_resolvers(str(resolver_file))


def test_register_user_resolvers_handles_runtime_error(tmp_path):
    resolver_file = tmp_path / "resolvers.py"
    resolver_file.write_text(
        "def pass_resolvers():\n    raise RuntimeError('broken')\n",
        encoding="utf-8",
    )
    sys.modules.pop("resolvers", None)

    resolvers.register_user_resolvers(str(resolver_file))


def test_register_user_resolvers_non_dict_result(tmp_path):
    resolver_file = tmp_path / "resolvers.py"
    resolver_file.write_text(
        "def pass_resolvers():\n    return ['bad']\n",
        encoding="utf-8",
    )
    sys.modules.pop("resolvers", None)

    resolvers.register_user_resolvers(str(resolver_file))


def test_register_user_resolvers_handles_resolver_registration_failure(
    monkeypatch, tmp_path
):
    resolver_file = tmp_path / "resolvers.py"
    resolver_file.write_text(
        "def pass_resolvers():\n    return {'broken': lambda value: value}\n",
        encoding="utf-8",
    )
    sys.modules.pop("resolvers", None)

    def _raise_for_broken(name, _func, replace=True):
        if name == "broken":
            raise RuntimeError("cannot register")

    monkeypatch.setattr(resolvers.OmegaConf, "register_new_resolver", _raise_for_broken)
    resolvers.register_user_resolvers(str(resolver_file))


def test_register_user_resolvers_non_dict_and_runtime_paths_with_priority_import(
    tmp_path,
):
    resolver_file = tmp_path / "resolvers.py"

    sys.path.insert(0, str(tmp_path))
    try:
        resolver_file.write_text(
            "def pass_resolvers():\n    return ['not-a-dict']\n",
            encoding="utf-8",
        )
        sys.modules.pop("resolvers", None)
        resolvers.register_user_resolvers(str(resolver_file))

        resolver_file.write_text(
            "def pass_resolvers():\n    raise RuntimeError('boom')\n",
            encoding="utf-8",
        )
        sys.modules.pop("resolvers", None)
        resolvers.register_user_resolvers(str(resolver_file))
    finally:
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
        sys.modules.pop("resolvers", None)


def test_register_user_resolvers_registers_valid_items_and_skips_bad_ones(
    monkeypatch, tmp_path
):
    resolver_file = tmp_path / "resolvers.py"
    resolver_file.write_text(
        "def pass_resolvers():\n    return {'ok': lambda value: value, 'broken': lambda value: value}\n",
        encoding="utf-8",
    )

    registered = []

    def _register(name, _func, replace=True):
        if name == "broken":
            raise RuntimeError("cannot register")
        registered.append(name)

    monkeypatch.setattr(resolvers.OmegaConf, "register_new_resolver", _register)

    sys.path.insert(0, str(tmp_path))
    try:
        sys.modules.pop("resolvers", None)
        resolvers.register_user_resolvers(str(resolver_file))
    finally:
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
        sys.modules.pop("resolvers", None)

    assert registered == ["ok"]
