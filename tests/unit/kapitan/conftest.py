# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from argparse import Namespace

import pytest

from kapitan import cached
from tests.support.paths import KAPITAN_LINT_FIXTURE
from tests.support.projects import prepare_isolated_project


@pytest.fixture
def targets_compile_args():
    """Factory for kapitan.targets.compile_targets args."""
    defaults = {
        "targets": None,
        "labels": None,
        "parallelism": 1,
        "force_fetch": False,
        "fetch": False,
        "force": False,
        "output_path": None,
        "inventory_pool_cache": False,
        "verbose": False,
    }

    def _make(**overrides):
        args = defaults.copy()
        args.update(overrides)
        return Namespace(**args)

    return _make


@pytest.fixture
def restore_cached_state():
    """Restore kapitan.cached module state after test mutation."""
    state = cached.as_dict()
    yield
    cached.from_dict(state)


@pytest.fixture
def isolated_lint_project(tmp_path, monkeypatch):
    """
    Create an isolated copy of the lint fixture project for test execution.
    Returns the path to the isolated copy.
    """
    return prepare_isolated_project(
        tmp_path, monkeypatch, KAPITAN_LINT_FIXTURE, "lint_project"
    )
