#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Test loading flags from .kapitan file - refactored for pytest."""

import os

import pytest
import yaml

from kapitan.inventory import InventoryBackends
from kapitan.utils import from_dot_kapitan


@pytest.fixture
def work_dir_with_kapitan(temp_dir):
    """Create a working directory and change to it for .kapitan tests."""
    original_dir = os.getcwd()
    os.chdir(temp_dir)

    def setup_dot_kapitan(config):
        """Helper to set up .kapitan file with given config."""
        with open(os.path.join(temp_dir, ".kapitan"), "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f)

    yield {
        "path": temp_dir,
        "setup_dot_kapitan": setup_dot_kapitan,
    }

    os.chdir(original_dir)


class TestFromDotKapitan:
    """Test loading flags from .kapitan file."""

    def test_no_file(self, work_dir_with_kapitan):
        """Test behavior when no .kapitan file exists."""
        assert from_dot_kapitan("compile", "inventory-path", "./some/fallback") == "./some/fallback"

    def test_no_option(self, work_dir_with_kapitan):
        """Test behavior when .kapitan file exists but doesn't have the requested option."""
        work_dir_with_kapitan["setup_dot_kapitan"](
            {
                "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert from_dot_kapitan("inventory", "inventory-path", "./some/fallback") == "./some/fallback"

    def test_cmd_option(self, work_dir_with_kapitan):
        """Test loading command-specific option from .kapitan file."""
        work_dir_with_kapitan["setup_dot_kapitan"](
            {
                "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert from_dot_kapitan("compile", "inventory-path", "./some/fallback") == "./path/to/inv"

    def test_global_option(self, work_dir_with_kapitan):
        """Test loading global option from .kapitan file."""
        work_dir_with_kapitan["setup_dot_kapitan"](
            {"global": {"inventory-path": "./some/path"}, "compile": {"inventory-path": "./path/to/inv"}}
        )
        assert from_dot_kapitan("inventory", "inventory-path", "./some/fallback") == "./some/path"

    def test_command_over_global_option(self, work_dir_with_kapitan):
        """Test that command-specific options take precedence over global options."""
        work_dir_with_kapitan["setup_dot_kapitan"](
            {"global": {"inventory-path": "./some/path"}, "compile": {"inventory-path": "./path/to/inv"}}
        )
        assert from_dot_kapitan("compile", "inventory-path", "./some/fallback") == "./path/to/inv"
