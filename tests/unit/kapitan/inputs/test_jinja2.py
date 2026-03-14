#!/usr/bin/env python3

from kapitan import cached, defaults
from kapitan.inputs.jinja2 import Jinja2
from kapitan.inventory.model.input_types import KapitanInputTypeJinja2Config


def test_compile_file_renders_and_strips_suffix(
    tmp_path, ref_controller, input_args, restore_cached_state
):
    target_name = "test-target"
    cached.global_inv = {
        target_name: {
            "parameters": {
                "kapitan": {
                    "vars": {"foo": "bar"},
                }
            }
        }
    }

    template_path = tmp_path / "template.j2"
    template_path.write_text(
        "vars={{ foo }} params={{ input_params.value }} path={{ input_params.compile_path }}",
        encoding="utf-8",
    )

    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    jinja2_input = Jinja2(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name=target_name,
        args=input_args(jinja2_filters=defaults.DEFAULT_JINJA2_FILTERS_PATH),
    )

    config = KapitanInputTypeJinja2Config(
        input_paths=[str(template_path)],
        output_path="",
        input_params={"value": "from_params"},
        suffix_remove=True,
        suffix_stripped=".j2",
    )

    jinja2_input.compile_file(config, str(template_path), str(compile_path))

    output_file = compile_path / "template"
    content = output_file.read_text(encoding="utf-8")
    expected = f"vars=bar params=from_params path={compile_path}"
    assert content == expected


def test_compile_file_keeps_suffix_when_strip_condition_does_not_match(
    tmp_path, ref_controller, input_args, restore_cached_state
):
    target_name = "test-target"
    cached.global_inv = {
        target_name: {
            "parameters": {
                "kapitan": {
                    "vars": {"foo": "bar"},
                }
            }
        }
    }

    template_path = tmp_path / "template.j2"
    template_path.write_text("vars={{ foo }}", encoding="utf-8")
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    jinja2_input = Jinja2(
        compile_path=str(compile_path),
        search_paths=[str(tmp_path)],
        ref_controller=ref_controller,
        target_name=target_name,
        args=input_args(jinja2_filters=defaults.DEFAULT_JINJA2_FILTERS_PATH),
    )
    config = KapitanInputTypeJinja2Config(
        input_paths=[str(template_path)],
        output_path="",
        input_params={},
        suffix_remove=True,
        suffix_stripped=".txt",
    )

    jinja2_input.compile_file(config, str(template_path), str(compile_path))
    assert (compile_path / "template.j2").is_file()
