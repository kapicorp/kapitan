# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from kapitan.cli import main as kapitan
from kapitan.inputs.copy import Copy
from kapitan.inputs.remove import Remove
from kapitan.inventory.model.input_types import (
    KapitanInputTypeCopyConfig,
    KapitanInputTypeRemoveConfig,
)


search_path = ""
ref_controller = ""


def test_remove_file_folder(input_compile_workspace, sample_pod_manifest):
    base_path = input_compile_workspace
    compile_path = base_path / "compiled"
    file_path = base_path / "input"
    test_file_path = file_path / "test_copy_input"
    test_file_compiled_path = compile_path / "test_copy_input"

    copy_compiler = Copy(str(compile_path), search_path, ref_controller, None, None)
    remove_compiler = Remove(str(compile_path), search_path, ref_controller, None, None)

    file_path.mkdir(exist_ok=True)
    test_file_path.write_text(sample_pod_manifest, encoding="utf-8")

    copy_config = KapitanInputTypeCopyConfig(
        input_paths=[str(file_path)], output_path=""
    )
    copy_compiler.compile_file(copy_config, str(test_file_path), str(compile_path))

    assert test_file_compiled_path.exists()

    remove_config = KapitanInputTypeRemoveConfig(
        input_paths=[str(test_file_compiled_path)]
    )
    remove_compiler.compile_file(
        remove_config, str(test_file_compiled_path), str(compile_path)
    )
    assert not test_file_compiled_path.exists()


def test_remove_folder_folder(input_compile_workspace, sample_pod_manifest):
    base_path = input_compile_workspace
    compile_path = base_path / "compiled"
    file_path = base_path / "input"
    test_file_path = file_path / "test_copy_input"
    test_file_compiled_path = compile_path / "test_copy_input"

    copy_compiler = Copy(str(compile_path), search_path, ref_controller, None, None)
    remove_compiler = Remove(str(compile_path), search_path, ref_controller, None, None)

    file_path.mkdir(exist_ok=True)
    test_file_path.write_text(sample_pod_manifest, encoding="utf-8")

    copy_config = KapitanInputTypeCopyConfig(
        input_paths=[str(file_path)], output_path=""
    )
    copy_compiler.compile_file(copy_config, str(test_file_path), str(compile_path))

    assert compile_path.exists()
    remove_config = KapitanInputTypeRemoveConfig(
        input_paths=[str(test_file_compiled_path)]
    )
    remove_compiler.compile_file(remove_config, str(compile_path), str(compile_path))
    assert not compile_path.exists()


def _validate_files_were_removed(base_path: Path):
    original_filepath = base_path / "copy_target"
    assert original_filepath.exists()
    removed_file = base_path / "compiled" / "removal" / "copy_target"
    assert not removed_file.exists()


def test_compiled_remove_target(isolated_kubernetes_inventory):
    kapitan("compile", "-t", "removal")
    _validate_files_were_removed(Path(isolated_kubernetes_inventory))


def test_remove_file_logs_oserror_and_continues(
    tmp_path, caplog, input_args, monkeypatch
):
    target_file = tmp_path / "artifact.txt"
    target_file.write_text("data", encoding="utf-8")

    remove_compiler = Remove(str(tmp_path), "", "", "test", input_args())
    remove_config = KapitanInputTypeRemoveConfig(input_paths=[str(target_file)])

    def _failing_remove(_path):
        raise OSError("cannot remove file")

    monkeypatch.setattr("kapitan.inputs.remove.os.remove", _failing_remove)
    with caplog.at_level("ERROR", logger="kapitan.inputs.remove"):
        remove_compiler.compile_file(remove_config, str(target_file), str(tmp_path))

    assert any("Input dir not removed" in message for message in caplog.messages)
