# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import filecmp
import hashlib
from pathlib import Path

from kapitan.cli import main as kapitan
from kapitan.inputs.copy import Copy
from kapitan.inventory.model.input_types import KapitanInputTypeCopyConfig
from kapitan.utils import directory_hash


def _bootstrap_copy_workspace(base_path: Path, file_content: str):
    file_path = base_path / "input"
    compile_path = base_path / "output"
    file_path.mkdir(exist_ok=True)
    compile_path.mkdir(exist_ok=True)
    test_file_path = file_path / "test_copy_input"
    test_file_path.write_text(file_content, encoding="utf-8")
    return file_path, compile_path, test_file_path


def test_copy_file_folder(input_compile_workspace, sample_pod_manifest):
    file_path, compile_path, test_file_path = _bootstrap_copy_workspace(
        input_compile_workspace, sample_pod_manifest
    )
    test_file_compiled_path = compile_path / "test_copy_input"
    copy_compiler = Copy(str(compile_path), "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[str(test_file_path)], output_path=str(compile_path)
    )
    copy_compiler.compile_file(config, str(test_file_path), str(compile_path))
    test_file_hash = hashlib.sha1(sample_pod_manifest.encode()).digest()
    test_file_compiled_hash = hashlib.sha1(
        test_file_compiled_path.read_text(encoding="utf-8").encode()
    ).digest()
    assert test_file_hash == test_file_compiled_hash


def test_copy_folder_folder(input_compile_workspace, sample_pod_manifest):
    file_path, compile_path, _ = _bootstrap_copy_workspace(
        input_compile_workspace, sample_pod_manifest
    )
    copy_compiler = Copy(str(compile_path), "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[str(file_path)], output_path=str(compile_path)
    )
    copy_compiler.compile_file(config, str(file_path), str(compile_path))
    file_path_hash = directory_hash(str(file_path))
    compile_path_hash = directory_hash(str(compile_path))
    assert file_path_hash == compile_path_hash


def test_copy_missing_path_folder(input_compile_workspace, sample_pod_manifest):
    file_path, compile_path, test_file_path = _bootstrap_copy_workspace(
        input_compile_workspace, sample_pod_manifest
    )
    copy_compiler = Copy(str(compile_path), "", "", "test", None)
    test_file_missing_path = file_path / "test_copy_input_missing"
    config = KapitanInputTypeCopyConfig(
        input_paths=[str(test_file_path)], output_path=str(compile_path)
    )
    copy_compiler.compile_file(config, str(test_file_missing_path), str(compile_path))


def _validate_files_were_copied(base_path: Path) -> None:
    original_filepath = base_path / "components" / "busybox" / "pod.yml"
    copied_filepath = base_path / "compiled" / "busybox" / "copy" / "pod.yml"
    assert filecmp.cmp(str(original_filepath), str(copied_filepath))

    original_filepath = base_path / "copy_target"
    copied_filepath = base_path / "compiled" / "busybox" / "copy" / "copy_target"
    assert filecmp.cmp(str(original_filepath), str(copied_filepath))

    original_filepath = base_path / "copy_target"
    copied_filepath = base_path / "compiled" / "busybox" / "copy_target"
    assert filecmp.cmp(str(original_filepath), str(copied_filepath))


def test_compiled_copy_target(isolated_kubernetes_inventory):
    kapitan("compile", "-t", "busybox")
    _validate_files_were_copied(Path(isolated_kubernetes_inventory))


def test_compiled_copy_all_targets(isolated_kubernetes_inventory):
    kapitan("compile")
    _validate_files_were_copied(Path(isolated_kubernetes_inventory))


def test_copy_overwrites_existing_destination_file(
    input_compile_workspace, sample_pod_manifest
):
    file_path, compile_path, test_file_path = _bootstrap_copy_workspace(
        input_compile_workspace, sample_pod_manifest
    )
    destination_file = compile_path / "existing.txt"
    destination_file.write_text("stale", encoding="utf-8")

    copy_compiler = Copy(str(compile_path), "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[str(test_file_path)], output_path=str(compile_path)
    )
    copy_compiler.compile_file(config, str(test_file_path), str(destination_file))

    assert destination_file.read_text(encoding="utf-8") == sample_pod_manifest


def test_copy_missing_path_with_ignore_missing_true(
    input_compile_workspace, sample_pod_manifest
):
    file_path, compile_path, _ = _bootstrap_copy_workspace(
        input_compile_workspace, sample_pod_manifest
    )
    missing_path = file_path / "does-not-exist"
    copy_compiler = Copy(str(compile_path), "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[str(missing_path)],
        output_path=str(compile_path),
        ignore_missing=True,
    )

    copy_compiler.compile_file(config, str(missing_path), str(compile_path))
    assert compile_path.is_dir()
