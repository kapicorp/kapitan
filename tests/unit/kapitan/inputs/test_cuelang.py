# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
from types import SimpleNamespace

import pytest
import yaml

from kapitan.errors import KustomizeTemplateError
from kapitan.inputs.cuelang import Cuelang
from kapitan.inventory.model.input_types import KapitanInputTypeCuelangConfig
from tests.support.paths import CUE_FIXTURE_MODULE1


pytestmark = pytest.mark.requires_cue

if shutil.which("cue") is None:
    pytest.skip("cue binary not found", allow_module_level=True)


def test_compile_file(tmp_path):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()
    args = type("Args", (), {"cue_path": "cue"})()

    temp_dir = tmp_path / "cue"
    shutil.copytree(CUE_FIXTURE_MODULE1, temp_dir, dirs_exist_ok=True)

    config = KapitanInputTypeCuelangConfig(
        input_paths=[str(temp_dir)],
        output_path=str(compile_path),
        input_fill_path="input:",
        input={"numerator": 10, "denominator": 2},
        output_yield_path="output",
    )

    cue_input = Cuelang(
        compile_path=str(compile_path),
        search_paths=[],
        ref_controller=None,
        target_name="test_target",
        args=args,
    )

    cue_input.compile_file(config, str(temp_dir), str(compile_path))

    output_file = compile_path / "output.yaml"
    assert os.path.exists(output_file)

    with open(output_file, encoding="utf-8") as handle:
        output = yaml.safe_load(handle)
        assert output == {"result": 5}


def test_compile_file_without_optional_flags(tmp_path, monkeypatch):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()
    args = type("Args", (), {"cue_path": "cue"})()

    temp_dir = tmp_path / "cue"
    shutil.copytree(CUE_FIXTURE_MODULE1, temp_dir, dirs_exist_ok=True)

    captured = {}

    def _run(cmd, stdout, stderr, text, cwd, check):
        captured["cmd"] = cmd
        stdout.write("result: 5\n")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("kapitan.inputs.cuelang.subprocess.run", _run)

    config = KapitanInputTypeCuelangConfig(
        input_paths=[str(temp_dir)],
        output_path=str(compile_path),
        input={"numerator": 10, "denominator": 2},
        input_fill_path=None,
        output_yield_path=None,
    )

    cue_input = Cuelang(
        compile_path=str(compile_path),
        search_paths=[],
        ref_controller=None,
        target_name="test_target",
        args=args,
    )
    cue_input.compile_file(config, str(temp_dir), str(compile_path))

    assert "-l" not in captured["cmd"]
    assert "--expression" not in captured["cmd"]


def test_compile_file_raises_on_cue_export_error(tmp_path, monkeypatch):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()
    args = type("Args", (), {"cue_path": "cue"})()

    temp_dir = tmp_path / "cue"
    shutil.copytree(CUE_FIXTURE_MODULE1, temp_dir, dirs_exist_ok=True)

    monkeypatch.setattr(
        "kapitan.inputs.cuelang.subprocess.run",
        lambda *_, **__: SimpleNamespace(returncode=1, stderr="boom"),
    )

    config = KapitanInputTypeCuelangConfig(
        input_paths=[str(temp_dir)],
        output_path=str(compile_path),
        input_fill_path="input:",
        input={"numerator": 10, "denominator": 2},
        output_yield_path="output",
    )

    cue_input = Cuelang(
        compile_path=str(compile_path),
        search_paths=[],
        ref_controller=None,
        target_name="test_target",
        args=args,
    )
    with pytest.raises(KustomizeTemplateError, match="Failed to run CUE export"):
        cue_input.compile_file(config, str(temp_dir), str(compile_path))
