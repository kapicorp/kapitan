#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for kapitan.utils.version (FR-009)."""

from kapitan.utils.version import compare_versions


class TestCompareVersions:
    """Characterize compare_versions — already has tests in test_version.py but
    those import from kapitan.utils; these test the new submodule path."""

    def test_equal_versions(self):
        assert compare_versions("0.30.0", "0.30.0") == "equal"

    def test_greater_major(self):
        assert compare_versions("1.0.0", "0.9.0") == "greater"

    def test_lower_minor(self):
        assert compare_versions("0.29.0", "0.30.0") == "lower"

    def test_greater_patch(self):
        assert compare_versions("0.30.1", "0.30.0") == "greater"

    def test_rc_is_lower_than_release(self):
        assert compare_versions("0.30.0-rc.1", "0.30.0") == "lower"

    def test_release_is_greater_than_rc(self):
        assert compare_versions("0.30.0", "0.30.0-rc.1") == "greater"

    def test_two_rcs_same_version_are_equal(self):
        assert compare_versions("0.30.0-rc.1", "0.30.0-rc.1") == "equal"

    def test_two_rcs_different_number_differ(self):
        assert compare_versions("0.30.0-rc.1", "0.30.0-rc.2") == "lower"
