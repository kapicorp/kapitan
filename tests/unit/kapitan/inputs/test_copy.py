# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import filecmp
import hashlib
import os

from kapitan.cli import main as kapitan
from kapitan.inputs.copy import Copy
from kapitan.inventory.model.input_types import KapitanInputTypeCopyConfig
from kapitan.utils import directory_hash


def _dirs_bootstrap_helper(base_path: str, file_content: str):
    file_path = os.path.join(base_path, "input")
    compile_path = os.path.join(base_path, "output")
    os.makedirs(file_path, exist_ok=True)
    os.makedirs(compile_path, exist_ok=True)
    test_file_path = os.path.join(file_path, "test_copy_input")
    with open(test_file_path, "w", encoding="utf-8") as handle:
        handle.write(file_content)
    return file_path, compile_path, test_file_path


def test_copy_file_folder(isolated_compile_dir, sample_pod_manifest):
    file_path, compile_path, test_file_path = _dirs_bootstrap_helper(
        os.getcwd(), sample_pod_manifest
    )
    test_file_compiled_path = os.path.join(compile_path, "test_copy_input")
    copy_compiler = Copy(compile_path, "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[test_file_path], output_path=compile_path
    )
    copy_compiler.compile_file(config, test_file_path, compile_path)
    test_file_hash = hashlib.sha1(sample_pod_manifest.encode()).digest()
    with open(test_file_compiled_path, encoding="utf-8") as handle:
        test_file_compiled_hash = hashlib.sha1(handle.read().encode()).digest()
        assert test_file_hash == test_file_compiled_hash


def test_copy_folder_folder(isolated_compile_dir, sample_pod_manifest):
    file_path, compile_path, _ = _dirs_bootstrap_helper(
        os.getcwd(), sample_pod_manifest
    )
    copy_compiler = Copy(compile_path, "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[file_path], output_path=compile_path
    )
    copy_compiler.compile_file(config, file_path, compile_path)
    file_path_hash = directory_hash(file_path)
    compile_path_hash = directory_hash(compile_path)
    assert file_path_hash == compile_path_hash


def test_copy_missing_path_folder(isolated_compile_dir, sample_pod_manifest):
    file_path, compile_path, test_file_path = _dirs_bootstrap_helper(
        os.getcwd(), sample_pod_manifest
    )
    copy_compiler = Copy(compile_path, "", "", "test", None)
    test_file_missing_path = os.path.join(file_path, "test_copy_input_missing")
    config = KapitanInputTypeCopyConfig(
        input_paths=[test_file_path], output_path=compile_path
    )
    copy_compiler.compile_file(config, test_file_missing_path, compile_path)


def _validate_files_were_copied(base_path: str) -> None:
    original_filepath = os.path.join(base_path, "components", "busybox", "pod.yml")
    copied_filepath = os.path.join(base_path, "compiled", "busybox", "copy", "pod.yml")
    assert filecmp.cmp(original_filepath, copied_filepath)

    original_filepath = os.path.join(base_path, "copy_target")
    copied_filepath = os.path.join(
        base_path, "compiled", "busybox", "copy", "copy_target"
    )
    assert filecmp.cmp(original_filepath, copied_filepath)

    original_filepath = os.path.join(base_path, "copy_target")
    copied_filepath = os.path.join(base_path, "compiled", "busybox", "copy_target")
    assert filecmp.cmp(original_filepath, copied_filepath)


def test_compiled_copy_target(isolated_kubernetes_inventory):
    kapitan("compile", "-t", "busybox")
    _validate_files_were_copied(os.getcwd())


def test_compiled_copy_all_targets(isolated_kubernetes_inventory):
    kapitan("compile")
    _validate_files_were_copied(os.getcwd())


def test_copy_overwrites_existing_destination_file(
    isolated_compile_dir, sample_pod_manifest
):
    file_path, compile_path, test_file_path = _dirs_bootstrap_helper(
        os.getcwd(), sample_pod_manifest
    )
    destination_file = os.path.join(compile_path, "existing.txt")
    with open(destination_file, "w", encoding="utf-8") as handle:
        handle.write("stale")

    copy_compiler = Copy(compile_path, "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[test_file_path], output_path=compile_path
    )
    copy_compiler.compile_file(config, test_file_path, destination_file)

    with open(destination_file, encoding="utf-8") as handle:
        assert handle.read() == sample_pod_manifest


def test_copy_missing_path_with_ignore_missing_true(
    isolated_compile_dir, sample_pod_manifest
):
    file_path, compile_path, _ = _dirs_bootstrap_helper(
        os.getcwd(), sample_pod_manifest
    )
    missing_path = os.path.join(file_path, "does-not-exist")
    copy_compiler = Copy(compile_path, "", "", "test", None)
    config = KapitanInputTypeCopyConfig(
        input_paths=[missing_path], output_path=compile_path, ignore_missing=True
    )

    copy_compiler.compile_file(config, missing_path, compile_path)
    assert os.path.isdir(compile_path)
