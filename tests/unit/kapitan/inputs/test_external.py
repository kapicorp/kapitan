# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import random
import string
import subprocess

import pytest

from kapitan.inputs.external import External
from kapitan.inventory.model.input_types import KapitanInputTypeExternalConfig
from tests.support.helpers import CompileTestHelper


def test_compile_external_target(isolated_test_resources, temp_dir):
    helper = CompileTestHelper(isolated_test_resources)
    helper.compile_with_args(
        ["compile", "--output-path", temp_dir, "-t", "external-test"]
    )
    assert os.path.isfile(
        os.path.join(temp_dir, "compiled", "external-test", "test.md")
    )


def test_compile_file(tmp_path):
    external_script_content = """
    #!/usr/bin/env bash
    set -ex

    name=$1
    compiled_target_dir=$2

    echo "test-${NAME}" > "${compiled_target_dir}/${name}"
    """
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()
    temp_dir = tmp_path / "script_dir"
    temp_dir.mkdir()
    external_script_file_path = temp_dir / "script.sh"
    external_script_file_path.write_text(external_script_content)

    search_paths = [str(external_script_file_path)]
    external_compiler = External(str(compile_path), search_paths, None, "test", None)

    name = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
    config = KapitanInputTypeExternalConfig(
        input_paths=[str(external_script_file_path)],
        output_path=str(compile_path),
        env_vars={"NAME": name},
        args=[name, r"\${compiled_target_dir}"],
    )

    with pytest.raises(ValueError) as excinfo:
        external_compiler.compile_file(
            config, str(external_script_file_path), str(compile_path)
        )

    assert "Executing external input with command" in excinfo.value.args[0]
    assert "failed" in excinfo.value.args[0]
    assert "Permission" in excinfo.value.args[0]

    subprocess.check_call(["chmod", "+x", str(external_script_file_path)])
    external_compiler.compile_file(
        config, str(external_script_file_path), str(compile_path)
    )

    generated_file = compile_path / name
    assert generated_file.is_file()
    assert generated_file.read_text() == f"test-{name}\n"


def test_compile_file_logs_oserror_and_continues(tmp_path, monkeypatch, caplog):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    external_compiler = External(str(compile_path), [], None, "test", None)
    config = KapitanInputTypeExternalConfig(
        input_paths=["/tmp/missing-script.sh"],
        output_path=str(compile_path),
        env_vars={},
        args=[],
    )

    def _raise_oserror(*_args, **_kwargs):
        raise OSError("cannot execute")

    monkeypatch.setattr("kapitan.inputs.external.subprocess.run", _raise_oserror)

    with caplog.at_level("ERROR", logger="kapitan.inputs.external"):
        external_compiler.compile_file(
            config, "/tmp/missing-script.sh", str(compile_path)
        )

    assert any("External failed to run" in message for message in caplog.messages)
