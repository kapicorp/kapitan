# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan


@pytest.fixture
def kapitan_runner(monkeypatch):
    """Run kapitan from an explicit project root within the test's monkeypatch scope."""

    def _run(project_root: str | Path, argv: list[str]) -> None:
        reset_cache()
        monkeypatch.chdir(Path(project_root))
        kapitan(*argv)

    return _run
