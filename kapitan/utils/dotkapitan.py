#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Dot-kapitan config file utilities for Kapitan."""

import logging
import os

import yaml

from kapitan import cached


logger = logging.getLogger(__name__)


def dot_kapitan_config():
    """Returns the parsed YAML .kapitan file. Subsequent requests will be cached"""
    if not cached.dot_kapitan:
        if os.path.exists(".kapitan"):
            with open(".kapitan") as f:
                cached.dot_kapitan = yaml.safe_load(f)

    return cached.dot_kapitan


def from_dot_kapitan(command, flag, default):
    """
    Returns the 'flag' from the '<command>' or from the 'global' section in the .kapitan file. If
    neither section provides a value for the flag, the value passed in `default` is returned.
    """
    kapitan_config = dot_kapitan_config()

    global_config = kapitan_config.get("global", {}) if kapitan_config else {}
    cmd_config = kapitan_config.get(command, {}) if kapitan_config else {}

    return cmd_config.get(flag, global_config.get(flag, default))
