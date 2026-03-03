#!/usr/bin/env python3

import builtins
import os
from types import SimpleNamespace

import pytest

from kapitan import cached
from kapitan.errors import CompileError
from kapitan.inputs import kadet as kadet_module
from kapitan.inputs.kadet import (
    Kadet,
    _to_dict,
    get_path_hash_from_input_kv,
    inventory_digest,
    inventory_frozen,
    load_from_search_paths,
    module_from_path,
    set_path_hash_input_kv,
    walk_and_hash,
)
from kapitan.inventory.model.input_types import KapitanInputTypeKadetConfig
from tests.support.helpers import read_yaml_file


def _write_kadet_module(path, content: str) -> None:
    path.mkdir()
    init_path = path / "__init__.py"
    init_path.write_text(content, encoding="utf-8")


def test_compile_file_writes_output(
    tmp_path, ref_controller, input_args, restore_cached_state
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    module_path = tmp_path / "kadet_module"
    _write_kadet_module(
        module_path,
        """
from kadet import BaseObj

def main(params=None):
    obj = BaseObj()
    obj.root.value = params.get("value")
    return {"output": obj}
""",
    )

    kadet_input = Kadet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )

    cached.inv = {"test-target": {"parameters": {}}}

    config = KapitanInputTypeKadetConfig(
        input_paths=[str(module_path)],
        output_path="",
        input_params={"value": "ok"},
        prune=False,
    )

    kadet_input.compile_file(config, str(module_path), str(compile_path))
    output_file = compile_path / "output.yaml"
    assert read_yaml_file(output_file) == {"value": "ok"}


def test_compile_file_invalid_main_signature(tmp_path, ref_controller, input_args):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    module_path = tmp_path / "kadet_invalid"
    _write_kadet_module(
        module_path,
        """

def main(a, b):
    return {}
""",
    )

    kadet_input = Kadet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )

    config = KapitanInputTypeKadetConfig(
        input_paths=[str(module_path)],
        output_path="",
        input_params={},
        prune=False,
    )

    with pytest.raises(ValueError):
        kadet_input.compile_file(config, str(module_path), str(compile_path))


def test_compile_file_raises_compile_error(tmp_path, ref_controller, input_args):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    module_path = tmp_path / "kadet_error"
    _write_kadet_module(
        module_path,
        """

def main():
    raise RuntimeError("boom")
""",
    )

    kadet_input = Kadet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )

    config = KapitanInputTypeKadetConfig(
        input_paths=[str(module_path)],
        output_path="",
        input_params={},
        prune=False,
    )

    with pytest.raises(CompileError):
        kadet_input.compile_file(config, str(module_path), str(compile_path))


def test_inventory_helpers_cache_and_target_lookup(restore_cached_state):
    cached.global_inv = {"target-a": {"parameters": {"value": 1}}}
    cached.inventory_global_kadet = None

    global_inventory = kadet_module.inventory_global(lazy=True)
    assert "target-a" in global_inventory

    token = kadet_module.current_target.set("target-a")
    try:
        inventory_obj = kadet_module.inventory(lazy=True)
    finally:
        kadet_module.current_target.reset(token)

    assert inventory_obj["parameters"]["value"] == 1


def test_inventory_frozen_and_digest_return_cached_inventory(restore_cached_state):
    cached.global_inv = {"target-a": {"parameters": {"value": 1}}}
    cached.inventory_global_kadet = None
    kadet_module.inventory_global.cache_clear()
    kadet_module.inventory_digest.cache_clear()

    token = kadet_module.current_target.set("target-a")
    try:
        frozen_inventory = inventory_frozen()
        digest = inventory_digest("target-a")
    finally:
        kadet_module.current_target.reset(token)
        kadet_module.inventory_global.cache_clear()
        kadet_module.inventory_digest.cache_clear()

    assert frozen_inventory is not None
    assert isinstance(digest, bytes)


def test_module_from_path_and_loader_error_paths(tmp_path, monkeypatch):
    with pytest.raises(FileNotFoundError):
        module_from_path(str(tmp_path / "missing"))

    module_dir = tmp_path / "my_component"
    _write_kadet_module(module_dir, "def main():\n    return {}\n")

    with pytest.raises(ModuleNotFoundError, match="does not match check_name"):
        module_from_path(str(module_dir), check_name="other_component")

    monkeypatch.setattr(kadet_module, "spec_from_file_location", lambda *_a, **_k: None)
    monkeypatch.setattr(kadet_module, "module_from_spec", lambda _spec: object())
    with pytest.raises(ModuleNotFoundError, match="Could not load module"):
        module_from_path(str(module_dir))


def test_load_from_search_paths_success_and_failure(tmp_path):
    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    module_dir = tmp_path / "component"
    _write_kadet_module(module_dir, "def main():\n    return {}\n")

    token = kadet_module.search_paths.set([str(missing_root), str(tmp_path)])
    try:
        loaded = load_from_search_paths("component")
    finally:
        kadet_module.search_paths.reset(token)

    assert loaded is not None

    token = kadet_module.search_paths.set([str(missing_root)])
    try:
        with pytest.raises(ModuleNotFoundError):
            load_from_search_paths("component")
    finally:
        kadet_module.search_paths.reset(token)


def test_compile_file_returns_without_writing_when_output_is_empty(
    tmp_path, ref_controller, input_args
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    module_path = tmp_path / "kadet_empty"
    _write_kadet_module(
        module_path,
        """
def main():
    return {}
""",
    )

    kadet_input = Kadet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )

    config = KapitanInputTypeKadetConfig(
        input_paths=[str(module_path)],
        output_path="",
        input_params={},
        prune=False,
    )

    kadet_input.compile_file(config, str(module_path), str(compile_path))
    assert list(compile_path.iterdir()) == []


def test_inputs_hash_is_stable_across_supported_input_types(
    tmp_path, ref_controller, input_args, restore_cached_state, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    cached.args = input_args(cache=True)
    cached.kapitan_input_kadet = None

    hashed_path = tmp_path / "hashed-input"
    _write_kadet_module(hashed_path, "def main():\n    return {}\n")
    (hashed_path / "nested.txt").write_text("data", encoding="utf-8")
    (hashed_path / "__pycache__").mkdir()
    (hashed_path / "__pycache__" / "ignored.pyc").write_bytes(b"ignored")

    kadet_input = Kadet(
        compile_path=str(tmp_path / "compiled"),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(cache=True),
    )

    first_hash = kadet_input.inputs_hash(
        {"b": 2, "a": 1},
        [2, 1],
        "test-target",
        3,
        b"abc",
        hashed_path,
    )
    second_hash = kadet_input.inputs_hash(
        hashed_path,
        b"abc",
        3,
        "test-target",
        [2, 1],
        {"a": 1, "b": 2},
    )
    unsupported_hash = kadet_input.inputs_hash(
        {"a": 1, "b": 2},
        [2, 1],
        "test-target",
        3,
        b"abc",
        object(),
        hashed_path,
    )

    assert first_hash == second_hash
    assert first_hash == unsupported_hash
    assert cached.kapitan_input_kadet is not None
    assert str(hashed_path / "__init__.py") in cached.kapitan_input_kadet.kv_cache
    assert str(hashed_path / "nested.txt") in cached.kapitan_input_kadet.kv_cache


def test_to_dict_handles_nested_lists_and_plain_values():
    nested = [{"a": 1}, ["x", {"y": 2}], "plain"]
    assert _to_dict(nested) == [{"a": 1}, ["x", {"y": 2}], "plain"]


def test_compile_file_zero_arg_main_writes_output(
    tmp_path, ref_controller, input_args, restore_cached_state
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    module_path = tmp_path / "kadet_zero_args"
    _write_kadet_module(
        module_path,
        """
def main():
    return {"result": {"value": "ok"}}
""",
    )

    kadet_input = Kadet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )
    cached.inv = {"test-target": {"parameters": {}}}

    config = KapitanInputTypeKadetConfig(
        input_paths=[str(module_path)],
        output_path="",
        input_params={},
        prune=False,
    )

    kadet_input.compile_file(config, str(module_path), str(compile_path))
    assert read_yaml_file(compile_path / "result.yaml") == {"value": "ok"}


def test_compile_file_uses_cached_output_when_cache_enabled(
    tmp_path, ref_controller, input_args, restore_cached_state, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    cached.args = input_args(cache=True)
    cached.inv = {"test-target": {"parameters": {}}}
    cached.global_inv = {"test-target": {"parameters": {}}}
    cached.inventory_global_kadet = None
    cached.kapitan_input_kadet = None
    kadet_module.inventory_global.cache_clear()
    kadet_module.inventory_digest.cache_clear()

    compile_path = tmp_path / "compiled-miss"
    compile_path.mkdir()
    cached_compile_path = tmp_path / "compiled-hit"
    cached_compile_path.mkdir()

    module_path = tmp_path / "kadet_cached_module"
    _write_kadet_module(
        module_path,
        """
def main():
    return {"cached": {"value": "ok"}}
""",
    )

    kadet_input = Kadet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(cache=True),
    )

    config = KapitanInputTypeKadetConfig(
        input_paths=[str(module_path)],
        output_path="",
        input_params={},
        prune=False,
    )

    kadet_input.compile_file(config, str(module_path), str(compile_path))
    assert read_yaml_file(compile_path / "cached.yaml") == {"value": "ok"}

    (module_path / "__init__.py").write_text(
        "def main():\n    raise RuntimeError('should not execute on cache hit')\n",
        encoding="utf-8",
    )

    kadet_input.compile_file(config, str(module_path), str(cached_compile_path))
    assert read_yaml_file(cached_compile_path / "cached.yaml") == {"value": "ok"}


def test_compile_file_covers_len_guard_fallthrough_branch(
    tmp_path, ref_controller, input_args, monkeypatch
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    module_path = tmp_path / "kadet_len_guard"
    _write_kadet_module(
        module_path,
        """
def main(params=None):
    return {"result": {"value": "ok"}}
""",
    )

    kadet_input = Kadet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )

    config = KapitanInputTypeKadetConfig(
        input_paths=[str(module_path)],
        output_path="",
        input_params={},
        prune=False,
    )

    sentinel_args = object()
    monkeypatch.setattr(
        kadet_module.inspect,
        "getfullargspec",
        lambda _func: SimpleNamespace(args=sentinel_args),
    )

    real_len = builtins.len

    class _LenResult(int):
        def __new__(cls):
            return int.__new__(cls, 2)

        def __gt__(self, _other):
            return False

        def __eq__(self, _other):
            return False

    def _len(obj):
        if obj is sentinel_args:
            return _LenResult()
        return real_len(obj)

    monkeypatch.setattr("builtins.len", _len)
    kadet_input.compile_file(config, str(module_path), str(compile_path))
    assert list(compile_path.iterdir()) == []


def test_walk_and_hash_ignores_missing_and_pycache_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    input_cache = kadet_module.InputCache("kadet")
    path_hash = kadet_module.InputCache.hash_object()
    empty_digest = path_hash.hexdigest()

    walk_and_hash(tmp_path / "missing", input_cache, path_hash)
    pycache_dir = tmp_path / "__pycache__"
    pycache_dir.mkdir()
    walk_and_hash(pycache_dir, input_cache, path_hash)
    empty_dir = tmp_path / "empty-dir"
    empty_dir.mkdir()
    walk_and_hash(empty_dir, input_cache, path_hash)
    fifo_path = tmp_path / "named-pipe"
    os.mkfifo(fifo_path)
    walk_and_hash(fifo_path, input_cache, path_hash)

    assert path_hash.hexdigest() == empty_digest


def test_path_hash_helpers_handle_disabled_cache(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("data", encoding="utf-8")

    assert get_path_hash_from_input_kv(path, False) is None
    set_path_hash_input_kv(path, b"digest", False)
