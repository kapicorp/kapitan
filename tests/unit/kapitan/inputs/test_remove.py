# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os

from kapitan.cli import main as kapitan
from kapitan.inputs.copy import Copy
from kapitan.inputs.remove import Remove
from kapitan.inventory.model.input_types import (
    KapitanInputTypeCopyConfig,
    KapitanInputTypeRemoveConfig,
)


search_path = ""
ref_controller = ""


def test_remove_file_folder(isolated_compile_dir, sample_pod_manifest):
    base_path = os.getcwd()
    compile_path = os.path.join(base_path, "compiled")
    file_path = os.path.join(base_path, "input")
    test_file_path = os.path.join(file_path, "test_copy_input")
    test_file_compiled_path = os.path.join(compile_path, "test_copy_input")

    copy_compiler = Copy(compile_path, search_path, ref_controller, None, None)
    remove_compiler = Remove(compile_path, search_path, ref_controller, None, None)

    os.makedirs(file_path, exist_ok=True)
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(sample_pod_manifest)

    copy_config = KapitanInputTypeCopyConfig(input_paths=[file_path], output_path="")
    copy_compiler.compile_file(copy_config, test_file_path, compile_path)

    assert os.path.exists(test_file_compiled_path)

    remove_config = KapitanInputTypeRemoveConfig(input_paths=[test_file_compiled_path])
    remove_compiler.compile_file(remove_config, test_file_compiled_path, compile_path)
    assert not os.path.exists(test_file_compiled_path)


def test_remove_folder_folder(isolated_compile_dir, sample_pod_manifest):
    base_path = os.getcwd()
    compile_path = os.path.join(base_path, "compiled")
    file_path = os.path.join(base_path, "input")
    test_file_path = os.path.join(file_path, "test_copy_input")
    test_file_compiled_path = os.path.join(compile_path, "test_copy_input")

    copy_compiler = Copy(compile_path, search_path, ref_controller, None, None)
    remove_compiler = Remove(compile_path, search_path, ref_controller, None, None)

    os.makedirs(file_path, exist_ok=True)
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(sample_pod_manifest)

    copy_config = KapitanInputTypeCopyConfig(input_paths=[file_path], output_path="")
    copy_compiler.compile_file(copy_config, test_file_path, compile_path)

    assert os.path.exists(compile_path)
    remove_config = KapitanInputTypeRemoveConfig(input_paths=[test_file_compiled_path])
    remove_compiler.compile_file(remove_config, compile_path, compile_path)
    assert not os.path.exists(compile_path)


def _validate_files_were_removed(base_path):
    original_filepath = os.path.join(base_path, "copy_target")
    assert os.path.exists(original_filepath)
    removed_file = os.path.join(base_path, "compiled", "removal", "copy_target")
    assert not os.path.exists(removed_file)


def test_compiled_remove_target(isolated_kubernetes_inventory):
    kapitan("compile", "-t", "removal")
    _validate_files_were_removed(os.getcwd())
