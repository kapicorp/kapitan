# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
import json
from pathlib import Path
from typing import Any, List, Optional

import yaml

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan
from kapitan.utils import directory_hash


class CompileTestHelper:
    """Utilities for inspecting compiled test output."""

    def __init__(self, isolated_path: str | Path):
        """
        Initialize compile test helper.

        Args:
            isolated_path: Path to isolated test directory
        """
        self.isolated_path = Path(isolated_path)

    def get_compiled_output(self, relative_path: str) -> str:
        """
        Read compiled output file.

        Args:
            relative_path: Path relative to compiled/ directory

        Returns:
            File contents as string
        """
        compiled_path = self.isolated_path / "compiled" / relative_path
        return compiled_path.read_text(encoding="utf-8")

    def verify_compiled_output_exists(self, relative_path: str) -> bool:
        """
        Check if compiled output exists.

        Args:
            relative_path: Path relative to compiled/ directory

        Returns:
            True if file exists
        """
        compiled_path = self.isolated_path / "compiled" / relative_path
        return compiled_path.exists()

    def compare_compiled_dirs(self, expected_dir: str | Path) -> bool:
        """
        Compare compiled output with expected directory.

        Args:
            expected_dir: Path to expected output directory

        Returns:
            True if directories match
        """
        compiled_dir = self.isolated_path / "compiled"
        compiled_hash = directory_hash(str(compiled_dir))
        expected_hash = directory_hash(str(expected_dir))
        return compiled_hash == expected_hash


def run_kapitan_in_project(project_root: str | Path, argv: List[str]) -> None:
    """
    Run Kapitan CLI from an explicit project root.
    """
    reset_cache()
    with contextlib.chdir(Path(project_root)):
        kapitan(*argv)


def compile_targets_in_project(
    project_root: str | Path,
    targets: Optional[List[str]] = None,
    extra_args: Optional[List[str]] = None,
) -> None:
    """
    Run `kapitan compile` from an explicit project root.
    """
    args = ["compile"]

    if targets:
        for target in targets:
            args.extend(["-t", target])

    if extra_args:
        args.extend(extra_args)

    run_kapitan_in_project(project_root, args)


def write_text_file(path: str | Path, content: str) -> Path:
    """
    Write text content to a file and return the Path.
    """
    file_path = Path(path)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def read_yaml_file(path: str | Path) -> Any:
    """
    Read a YAML file and return the parsed content.
    """
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def read_json_file(path: str | Path) -> Any:
    """
    Read a JSON file and return the parsed content.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assert_compiled_output_exists(
    base_path: str | Path,
    relative_path: str,
    *,
    compiled_subdir: str | Path | None = None,
) -> Path:
    """
    Assert that a compiled output exists under compiled/ and return the Path.
    """
    compiled_path = Path(base_path) / "compiled"
    if compiled_subdir:
        compiled_path = compiled_path / compiled_subdir
    compiled_path = compiled_path / relative_path
    assert compiled_path.exists()
    return compiled_path
