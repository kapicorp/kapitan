# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from typing import Any

import yaml


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
