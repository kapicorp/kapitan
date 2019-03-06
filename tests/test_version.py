#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
