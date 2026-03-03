#!/usr/bin/env python3

import json
from types import SimpleNamespace

import pytest
import toml

from kapitan import cached
from kapitan.errors import CompileError, KapitanError
from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import (
    KapitanInputTypeCopyConfig,
    KapitanInputTypeJinja2Config,
    OutputType,
)


class DummyInput(InputType):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_paths = []

    def compile_input_path(self, comp_obj, input_path: str):
        self.seen_paths.append(input_path)

    def compile_file(self, config, input_path: str, compile_path: str):
        raise NotImplementedError


def _build_compiler(tmp_path, ref_controller, input_args):
    return DummyInput(
        compile_path=str(tmp_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )


def test_compile_obj_expands_inputs(tmp_path, ref_controller, input_args):
    input_file = tmp_path / "input.txt"
    input_file.write_text("data", encoding="utf-8")

    compiler = _build_compiler(tmp_path, ref_controller, input_args)

    comp_obj = SimpleNamespace(input_paths=["input.txt"], ignore_missing=False)
    compiler.compile_obj(comp_obj)

    assert compiler.seen_paths == [str(input_file)]


def test_compile_obj_ignore_missing(tmp_path, ref_controller, input_args):
    compiler = _build_compiler(tmp_path, ref_controller, input_args)

    comp_obj = SimpleNamespace(input_paths=["missing.txt"], ignore_missing=True)
    compiler.compile_obj(comp_obj)

    assert compiler.seen_paths == []


def test_cacheable_returns_false_by_default(tmp_path, ref_controller, input_args):
    compiler = _build_compiler(tmp_path, ref_controller, input_args)

    assert compiler.cacheable() is False


def test_compile_obj_missing_raises(tmp_path, ref_controller, input_args):
    compiler = _build_compiler(tmp_path, ref_controller, input_args)

    comp_obj = SimpleNamespace(input_paths=["missing.txt"], ignore_missing=False)
    with pytest.raises(CompileError):
        compiler.compile_obj(comp_obj)


def test_compile_obj_missing_error_contains_context(
    tmp_path, ref_controller, input_args
):
    compiler = _build_compiler(tmp_path, ref_controller, input_args)

    config = KapitanInputTypeCopyConfig(
        input_paths=["nonexistent/*.yaml"], output_path=".", ignore_missing=False
    )
    with pytest.raises(CompileError) as exc_info:
        compiler.compile_obj(config)

    message = str(exc_info.value)
    assert "nonexistent/*.yaml" in message
    assert "test-target" in message
    assert "not found" in message


def test_compile_obj_deduplicates_overlapping_search_paths(
    tmp_path, ref_controller, input_args
):
    input_file = tmp_path / "config.yaml"
    input_file.write_text("", encoding="utf-8")

    compiler = DummyInput(
        compile_path=str(tmp_path / "compiled"),
        search_paths=[str(tmp_path), str(tmp_path)],
        ref_controller=ref_controller,
        target_name="test-target",
        args=input_args(),
    )
    config = KapitanInputTypeCopyConfig(input_paths=["config.yaml"], output_path=".")
    compiler.compile_obj(config)

    assert compiler.seen_paths == [str(input_file)]


def test_compile_obj_mixed_found_and_missing_paths_with_ignore_missing(
    tmp_path, ref_controller, input_args
):
    input_file = tmp_path / "exists.yaml"
    input_file.write_text("", encoding="utf-8")

    compiler = _build_compiler(tmp_path, ref_controller, input_args)
    config = KapitanInputTypeCopyConfig(
        input_paths=["exists.yaml", "missing.yaml"],
        output_path=".",
        ignore_missing=True,
    )

    compiler.compile_obj(config)
    assert compiler.seen_paths == [str(input_file)]


def test_compile_obj_fails_fast_after_compiling_prior_valid_paths(
    tmp_path, ref_controller, input_args
):
    first_file = tmp_path / "file1.yaml"
    second_file = tmp_path / "file2.yaml"
    first_file.write_text("", encoding="utf-8")
    second_file.write_text("", encoding="utf-8")

    compiler = _build_compiler(tmp_path, ref_controller, input_args)
    config = KapitanInputTypeCopyConfig(
        input_paths=["file1.yaml", "missing.yaml", "file2.yaml"],
        output_path=".",
        ignore_missing=False,
    )

    with pytest.raises(CompileError):
        compiler.compile_obj(config)

    assert compiler.seen_paths == [str(first_file)]


def test_to_file_auto_json(tmp_path, ref_controller, input_args):
    compiler = _build_compiler(tmp_path, ref_controller, input_args)

    config = SimpleNamespace(output_type=OutputType.AUTO, prune=False)
    output_path = tmp_path / "output.json"
    compiler.to_file(config, str(output_path), {"hello": "world"})

    assert output_path.is_file()
    output_obj = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_obj == {"hello": "world"}


def test_to_file_invalid_output_type(tmp_path, ref_controller, input_args):
    compiler = _build_compiler(tmp_path, ref_controller, input_args)

    config = SimpleNamespace(output_type="invalid", prune=False)
    with pytest.raises(ValueError):
        compiler.to_file(config, str(tmp_path / "output"), {"hello": "world"})


class _NoopInput(InputType):
    def compile_file(self, config, input_path, compile_path):
        return None


class _FailingInput(InputType):
    def compile_file(self, config, input_path, compile_path):
        raise KapitanError("boom")


def test_compile_obj_missing_path_raises(tmp_path, input_args):
    compiler = _NoopInput(str(tmp_path), [str(tmp_path)], None, "target", input_args())
    config = KapitanInputTypeJinja2Config(
        input_paths=["missing.j2"], output_path="out", ignore_missing=False
    )

    with pytest.raises(CompileError):
        compiler.compile_obj(config)


def test_compile_input_path_wraps_kapitan_error(tmp_path, input_args):
    compiler = _FailingInput(
        str(tmp_path), [str(tmp_path)], None, "target", input_args()
    )
    config = KapitanInputTypeJinja2Config(
        input_paths=[str(tmp_path / "dummy.j2")], output_path="out"
    )

    with pytest.raises(CompileError):
        compiler.compile_input_path(config, str(tmp_path / "dummy.j2"))


class _NoopToFileInput(InputType):
    def compile_file(self, config, input_path, compile_path):
        return None


def _build_to_file_compiler(tmp_path, input_args):
    cached.inv = {"target": {"parameters": {}}}
    return _NoopToFileInput(str(tmp_path), [], None, "target", input_args())


def test_to_file_auto_json_from_dedicated_to_file_suite(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.AUTO
    )
    file_path = tmp_path / "output.json"

    compiler.to_file(config, str(file_path), {"a": 1})

    assert json.loads(file_path.read_text(encoding="utf-8")) == {"a": 1}


def test_to_file_plain_and_toml(tmp_path, input_args, restore_cached_state):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    plain_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.PLAIN
    )
    plain_path = tmp_path / "plain.txt"
    compiler.to_file(plain_config, str(plain_path), "hello")
    assert plain_path.read_text(encoding="utf-8") == "hello"

    toml_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.TOML
    )
    toml_path = tmp_path / "config"
    compiler.to_file(toml_config, str(toml_path), {"a": 1})
    assert toml.loads((tmp_path / "config.toml").read_text(encoding="utf-8")) == {
        "a": 1
    }


def test_to_file_invalid_output_type_raises(tmp_path, input_args, restore_cached_state):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    bad_config = SimpleNamespace(output_type="bad", prune=False)
    file_path = tmp_path / "output.bad"

    with pytest.raises(ValueError, match="not supported"):
        compiler.to_file(bad_config, str(file_path), {"a": 1})


def test_to_file_auto_without_extension_defaults_to_yaml(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.AUTO
    )
    file_path = tmp_path / "output"

    compiler.to_file(config, str(file_path), {"a": 1})
    assert (tmp_path / "output.yaml").is_file()


def test_to_file_auto_unknown_extension_defaults_to_yaml(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.AUTO
    )
    file_path = tmp_path / "output.unknown"

    compiler.to_file(config, str(file_path), {"a": 1})
    assert (tmp_path / "output.unknown.yaml").is_file()


def test_to_file_plain_with_reveal_true(tmp_path, input_args, restore_cached_state):
    compiler = _build_to_file_compiler(
        tmp_path, lambda **kwargs: input_args(reveal=True, **kwargs)
    )
    plain_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.PLAIN
    )
    plain_path = tmp_path / "revealed.txt"

    compiler.to_file(plain_config, str(plain_path), "hello")
    assert plain_path.read_text(encoding="utf-8") == "hello"


def test_to_file_yaml_style_selection_from_inventory(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    cached.inv["target"]["parameters"]["multiline_string_style"] = "literal"

    yaml_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.YAML
    )
    yaml_path = tmp_path / "styled"
    compiler.to_file(yaml_config, str(yaml_path), {"k": "line1\nline2"})

    content = (tmp_path / "styled.yaml").read_text(encoding="utf-8")
    assert "line1" in content
    assert "line2" in content


def test_to_file_yaml_style_selection_from_cli_args(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    cached.args = SimpleNamespace(multiline_string_style="literal")

    yaml_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.YAML
    )
    yaml_path = tmp_path / "styled-cli"
    compiler.to_file(yaml_config, str(yaml_path), {"k": "line1\nline2"})

    assert (tmp_path / "styled-cli.yaml").is_file()


def test_to_file_yaml_style_selection_from_legacy_cli_args(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(tmp_path, input_args)
    cached.args = SimpleNamespace(yaml_multiline_string_style="literal")

    yaml_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.YAML
    )
    yaml_path = tmp_path / "styled-legacy"
    compiler.to_file(yaml_config, str(yaml_path), {"k": "line1\nline2"})

    assert (tmp_path / "styled-legacy.yaml").is_file()


def test_to_file_yaml_reveal_empty_object_branch(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(
        tmp_path, lambda **kwargs: input_args(reveal=True, **kwargs)
    )
    yaml_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.YAML
    )
    yaml_path = tmp_path / "empty-yaml"
    compiler.to_file(yaml_config, str(yaml_path), {})

    assert (tmp_path / "empty-yaml.yaml").read_text(encoding="utf-8") == ""


def test_to_file_json_reveal_empty_object_branch(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(
        tmp_path, lambda **kwargs: input_args(reveal=True, **kwargs)
    )
    json_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.JSON
    )
    json_path = tmp_path / "empty-json"
    compiler.to_file(json_config, str(json_path), {})

    assert (tmp_path / "empty-json.json").read_text(encoding="utf-8") == ""


def test_to_file_toml_reveal_empty_object_branch(
    tmp_path, input_args, restore_cached_state
):
    compiler = _build_to_file_compiler(
        tmp_path, lambda **kwargs: input_args(reveal=True, **kwargs)
    )
    toml_config = KapitanInputTypeJinja2Config(
        input_paths=[], output_path="out", output_type=OutputType.TOML
    )
    toml_path = tmp_path / "empty-toml"
    compiler.to_file(toml_config, str(toml_path), {})

    assert (tmp_path / "empty-toml.toml").read_text(encoding="utf-8") == ""
