#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for kapitan.utils.dotkapitan (FR-009)."""

import pytest
import yaml

from kapitan.utils.dotkapitan import from_dot_kapitan


@pytest.fixture(autouse=True)
def _reset_dot_kapitan_cache(reset_cached_args):
    """Clear dot_kapitan cache before each test (uses reset_cached_args fixture)."""
    return


class TestFromDotKapitan:
    """Characterize from_dot_kapitan — reads config from .kapitan YAML file."""

    def test_returns_default_when_no_file(self, isolated_compile_dir):
        assert from_dot_kapitan("compile", "targets", ["default"]) == ["default"]

    def test_reads_cmd_section(self, isolated_compile_dir):
        with open(".kapitan", "w") as f:
            yaml.safe_dump({"compile": {"targets": ["foo"]}}, f)
        assert from_dot_kapitan("compile", "targets", []) == ["foo"]

    def test_reads_global_section_as_fallback(self, isolated_compile_dir):
        with open(".kapitan", "w") as f:
            yaml.safe_dump({"global": {"indent": 4}}, f)
        assert from_dot_kapitan("compile", "indent", 2) == 4

    def test_cmd_section_overrides_global(self, isolated_compile_dir):
        with open(".kapitan", "w") as f:
            yaml.safe_dump({"global": {"indent": 4}, "compile": {"indent": 8}}, f)
        assert from_dot_kapitan("compile", "indent", 2) == 8

    def test_missing_key_returns_default(self, isolated_compile_dir):
        with open(".kapitan", "w") as f:
            yaml.safe_dump({"compile": {}}, f)
        assert from_dot_kapitan("compile", "missing-key", "fallback") == "fallback"
