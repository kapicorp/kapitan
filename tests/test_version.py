#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"version check tests"

import unittest

from kapitan.utils import compare_versions


class VersionTest(unittest.TestCase):
    "Test version checks"

    def test_version_equal(self):
        dot_kapitan_version = "0.22.0"
        current_version = "0.22.0"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "equal")

    def test_version_rc_equal(self):
        dot_kapitan_version = "0.22.0-rc.1"
        current_version = "0.22.0-rc.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "equal")

    def test_version_major_equal(self):
        dot_kapitan_version = "0.22"
        current_version = "0.22.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "equal")

    def test_version_one_rc_major_equal(self):
        dot_kapitan_version = "0.22"
        current_version = "0.22.1-rc.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "equal")

    def test_version_greater(self):
        dot_kapitan_version = "0.22.1"
        current_version = "0.22.0"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "greater")

    def test_version_one_rc_greater(self):
        dot_kapitan_version = "0.22.0"
        current_version = "0.22.0-rc.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "greater")

    def test_version_both_rc_greater(self):
        dot_kapitan_version = "0.22.1-rc.1"
        current_version = "0.22.0-rc.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "greater")

    def test_version_both_rc_major_greater(self):
        dot_kapitan_version = "0.23.0-rc.1"
        current_version = "0.22.0-rc.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "greater")

    def test_version_lower(self):
        dot_kapitan_version = "0.22.0"
        current_version = "0.22.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "lower")

    def test_version_one_rc_lower(self):
        dot_kapitan_version = "0.22.0-rc.1"
        current_version = "0.22.0"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "lower")

    def test_version_both_rc_lower(self):
        dot_kapitan_version = "0.22.0-rc.1"
        current_version = "0.22.1-rc.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "lower")

    def test_version_both_rc_major_lower(self):
        dot_kapitan_version = "0.22.0-rc.1"
        current_version = "0.23.0-rc.1"
        result = compare_versions(dot_kapitan_version, current_version)
        self.assertEqual(result, "lower")