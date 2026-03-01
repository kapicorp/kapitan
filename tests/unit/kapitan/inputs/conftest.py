# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
from argparse import Namespace

import pytest

from kapitan import cached
from kapitan.cached import reset_cache
from tests.support.runtime import cached_args_defaults


@pytest.fixture
def isolated_compile_dir(temp_dir):
    """
    Create an isolated compilation directory with its own compiled/ output.
    Automatically resets cache and returns to original directory after test.
    """
    original_dir = os.getcwd()
    reset_cache()
    cached.args = cached_args_defaults()
    os.chdir(temp_dir)

    yield temp_dir

    os.chdir(original_dir)
    reset_cache()
    cached.args = cached_args_defaults()


@pytest.fixture
def input_args():
    """Factory for common input compiler args."""
    defaults = {
        "cache": False,
        "reveal": False,
        "indent": 2,
    }

    def _make(**overrides):
        args = defaults.copy()
        args.update(overrides)
        return Namespace(**args)

    return _make


@pytest.fixture
def sample_pod_manifest():
    return """\
apiVersion: v1
kind: Pod
metadata:
  name: alpine
  namespace: default
spec:
  containers:
  - image: alpine:3.2
    command:
      - /bin/sh
      - "-c"
      - "sleep 60m"
    imagePullPolicy: IfNotPresent
    name: alpine
  restartPolicy: Always
"""
