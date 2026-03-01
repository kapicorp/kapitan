# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import shutil
from pathlib import Path

from kapitan import cached
from kapitan.cached import reset_cache
from tests.support.runtime import cached_args_defaults


def copy_project_tree(
    tmp_path: Path, source_path: str | Path, destination_name: str
) -> Path:
    destination = tmp_path / destination_name
    shutil.copytree(source_path, destination)
    return destination


def prepare_isolated_project(
    tmp_path: Path,
    monkeypatch,
    source_path: str | Path,
    destination_name: str,
    *,
    clean_compiled: bool = False,
) -> Path:
    isolated_path = copy_project_tree(tmp_path, source_path, destination_name)
    reset_cache()
    cached.args = cached_args_defaults()
    monkeypatch.chdir(isolated_path)

    if clean_compiled:
        compiled_path = isolated_path / "compiled"
        if compiled_path.exists():
            shutil.rmtree(compiled_path)

    return isolated_path
