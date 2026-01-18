#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Critical edge case tests for InputType.compile_obj method"""

import os

import pytest

from kapitan.errors import CompileError
from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import KapitanInputTypeCopyConfig


class MockInputType(InputType):
    """Mock InputType for testing compile_obj edge cases"""

    def __init__(self, compile_path, search_paths, ref_controller, target_name, args):
        super().__init__(compile_path, search_paths, ref_controller, target_name, args)
        self.compiled_paths = []

    def compile_file(self, config, input_path, compile_path):
        """Mock compile_file that records the path"""
        self.compiled_paths.append(input_path)


class TestCompileObjEdgeCases:
    """Tests for critical edge cases in compile_obj method"""

    def test_deduplication_overlapping_search_paths(self, temp_dir):
        """Verify files aren't compiled multiple times when search paths overlap"""
        test_file = os.path.join(temp_dir, "config.yaml")
        open(test_file, "w").close()

        compile_path = os.path.join(temp_dir, "compiled")
        os.makedirs(compile_path, exist_ok=True)

        # Both search paths point to same directory
        input_type = MockInputType(
            compile_path, [temp_dir, temp_dir], None, "test-target", None
        )

        config = KapitanInputTypeCopyConfig(
            input_paths=["config.yaml"], output_path="."
        )
        input_type.compile_obj(config)

        # File should be compiled exactly once despite duplicate search paths
        assert len(input_type.compiled_paths) == 1
        assert input_type.compiled_paths[0] == test_file

    def test_ignore_missing_false_raises_error(self, temp_dir):
        """Verify CompileError is raised for missing paths when ignore_missing=False"""
        compile_path = os.path.join(temp_dir, "compiled")
        os.makedirs(compile_path, exist_ok=True)

        input_type = MockInputType(compile_path, [temp_dir], None, "test-target", None)

        config = KapitanInputTypeCopyConfig(
            input_paths=["nonexistent/*.yaml"], output_path=".", ignore_missing=False
        )

        with pytest.raises(CompileError) as exc_info:
            input_type.compile_obj(config)

        # Error should include helpful context
        assert "nonexistent/*.yaml" in str(exc_info.value)
        assert "test-target" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_ignore_missing_true_no_error(self, temp_dir):
        """Verify missing paths are silently skipped when ignore_missing=True"""
        compile_path = os.path.join(temp_dir, "compiled")
        os.makedirs(compile_path, exist_ok=True)

        input_type = MockInputType(compile_path, [temp_dir], None, "test-target", None)

        config = KapitanInputTypeCopyConfig(
            input_paths=["nonexistent/*.yaml"], output_path=".", ignore_missing=True
        )

        # Should not raise error
        input_type.compile_obj(config)

        # Nothing should be compiled
        assert len(input_type.compiled_paths) == 0

    def test_mixed_found_and_missing_paths_ignore_true(self, temp_dir):
        """Verify partial matches work correctly - compile found, skip missing"""
        test_file = os.path.join(temp_dir, "exists.yaml")
        open(test_file, "w").close()

        compile_path = os.path.join(temp_dir, "compiled")
        os.makedirs(compile_path, exist_ok=True)

        input_type = MockInputType(compile_path, [temp_dir], None, "test-target", None)

        config = KapitanInputTypeCopyConfig(
            input_paths=["exists.yaml", "missing.yaml"],
            output_path=".",
            ignore_missing=True,
        )

        # Should compile existing file without error
        input_type.compile_obj(config)

        assert len(input_type.compiled_paths) == 1
        assert input_type.compiled_paths[0] == test_file

    def test_incremental_compilation_behavior_on_error(self, temp_dir):
        """Verify files are compiled incrementally - valid paths compile before error occurs"""
        # Create two valid files
        file1 = os.path.join(temp_dir, "file1.yaml")
        file2 = os.path.join(temp_dir, "file2.yaml")
        open(file1, "w").close()
        open(file2, "w").close()

        compile_path = os.path.join(temp_dir, "compiled")
        os.makedirs(compile_path, exist_ok=True)

        input_type = MockInputType(compile_path, [temp_dir], None, "test-target", None)

        # Mix valid paths with a missing one in the middle
        config = KapitanInputTypeCopyConfig(
            input_paths=["file1.yaml", "missing.yaml", "file2.yaml"],
            output_path=".",
            ignore_missing=False,
        )

        # Should compile file1, then fail on missing.yaml
        with pytest.raises(CompileError):
            input_type.compile_obj(config)

        # file1 should have been compiled before the error
        # file2 should NOT be compiled (fail-fast after error)
        assert len(input_type.compiled_paths) == 1
        assert input_type.compiled_paths[0] == file1
