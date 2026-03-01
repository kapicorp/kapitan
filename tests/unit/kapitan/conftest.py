# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from argparse import Namespace

import pytest

from kapitan import cached


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
