#!/usr/bin/env python3

import builtins
import sys
from types import SimpleNamespace

import pytest

from kapitan import cached
from kapitan.errors import CompileError
from kapitan.inputs.jsonnet import Jsonnet, select_jsonnet_runtime
from kapitan.inventory.model.input_types import (
    KapitanInputTypeJsonnetConfig,
    OutputType,
)
from kapitan.resources import search_imports as search_imports_impl
from tests.support.helpers import read_json_file


pytest.importorskip("_jsonnet")


def test_compile_file_writes_json(tmp_path, ref_controller, input_args):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    jsonnet_file = tmp_path / "output.jsonnet"
    jsonnet_file.write_text('{"output": {"hello": "world"}}', encoding="utf-8")

    jsonnet_input = Jsonnet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(use_go_jsonnet=False),
    )

    config = KapitanInputTypeJsonnetConfig(
        input_paths=[str(jsonnet_file)],
        output_path="",
        output_type=OutputType.JSON,
        prune=False,
    )

    jsonnet_input.compile_file(config, str(jsonnet_file), str(compile_path))

    output_file = compile_path / "output.json"
    assert read_json_file(output_file) == {"hello": "world"}


def test_compile_file_wraps_non_dict_output(
    tmp_path, ref_controller, input_args, restore_cached_state
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    jsonnet_file = tmp_path / "array.jsonnet"
    jsonnet_file.write_text("[1, 2, 3]", encoding="utf-8")

    jsonnet_input = Jsonnet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(use_go_jsonnet=False),
    )

    cached.inv = {"test-target": {"parameters": {}}}

    config = KapitanInputTypeJsonnetConfig(
        input_paths=[str(jsonnet_file)],
        output_path="",
        output_type=OutputType.YAML,
        prune=False,
    )

    jsonnet_input.compile_file(config, str(jsonnet_file), str(compile_path))
    output_file = compile_path / "array.yaml"
    import yaml

    output_docs = list(yaml.safe_load_all(output_file.read_text(encoding="utf-8")))
    assert output_docs == [1, 2, 3]


def test_compile_file_invalid_jsonnet(tmp_path, ref_controller, input_args):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    jsonnet_file = tmp_path / "invalid.jsonnet"
    jsonnet_file.write_text("{:", encoding="utf-8")

    jsonnet_input = Jsonnet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(use_go_jsonnet=False),
    )

    config = KapitanInputTypeJsonnetConfig(
        input_paths=[str(jsonnet_file)],
        output_path="",
        output_type=OutputType.JSON,
        prune=False,
    )

    with pytest.raises(RuntimeError):
        jsonnet_input.compile_file(config, str(jsonnet_file), str(compile_path))


def test_select_jsonnet_runtime_use_go_module(monkeypatch):
    fake_go_jsonnet = SimpleNamespace(name="_gojsonnet")
    monkeypatch.setitem(sys.modules, "_gojsonnet", fake_go_jsonnet)

    assert select_jsonnet_runtime(True) is fake_go_jsonnet


def test_select_jsonnet_runtime_missing_modules_raises_helpful_error(monkeypatch):
    real_import = builtins.__import__
    monkeypatch.delitem(sys.modules, "_jsonnet", raising=False)
    monkeypatch.delitem(sys.modules, "_gojsonnet", raising=False)

    def _import(name, *args, **kwargs):
        if name in {"_jsonnet", "_gojsonnet"}:
            raise ImportError("missing jsonnet module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    with pytest.raises(ImportError, match="Jsonnet is not installed"):
        select_jsonnet_runtime(False)


def test_compile_file_wraps_runtime_errors(
    tmp_path, ref_controller, input_args, monkeypatch
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    jsonnet_file = tmp_path / "output.jsonnet"
    jsonnet_file.write_text('{"output": {"hello": "world"}}', encoding="utf-8")

    class _FailingRuntime:
        @staticmethod
        def evaluate_file(*_args, **_kwargs):
            raise CompileError("runtime failed")

    monkeypatch.setattr(
        "kapitan.inputs.jsonnet.select_jsonnet_runtime", lambda _use_go: _FailingRuntime
    )

    jsonnet_input = Jsonnet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(use_go_jsonnet=False),
    )
    config = KapitanInputTypeJsonnetConfig(
        input_paths=[str(jsonnet_file)],
        output_path="",
        output_type=OutputType.JSON,
        prune=False,
    )

    with pytest.raises(CompileError, match="Jsonnet Error compiling"):
        jsonnet_input.compile_file(config, str(jsonnet_file), str(compile_path))


def test_compile_file_with_import_uses_import_callback(
    tmp_path, ref_controller, input_args, monkeypatch
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    imported_file = tmp_path / "values.libsonnet"
    imported_file.write_text('{"hello": "world"}', encoding="utf-8")

    jsonnet_file = tmp_path / "with_import.jsonnet"
    jsonnet_file.write_text('{"output": import "values.libsonnet"}', encoding="utf-8")

    calls = []

    def _search_imports(cwd, imp, search_paths):
        calls.append((cwd, imp, tuple(search_paths)))
        return search_imports_impl(cwd, imp, search_paths)

    monkeypatch.setattr("kapitan.inputs.jsonnet.search_imports", _search_imports)

    jsonnet_input = Jsonnet(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(use_go_jsonnet=False),
    )
    config = KapitanInputTypeJsonnetConfig(
        input_paths=[str(jsonnet_file)],
        output_path="",
        output_type=OutputType.JSON,
        prune=False,
    )

    jsonnet_input.compile_file(config, str(jsonnet_file), str(compile_path))

    output_file = compile_path / "output.json"
    assert read_json_file(output_file) == {"hello": "world"}
    assert any(imp == "values.libsonnet" for _, imp, _ in calls)
