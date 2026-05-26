#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for kapitan.topics — cross-target parameter aggregation."""

import unittest

import pytest

from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.topics import topics


@pytest.mark.usefixtures("reset_cached_args")
class TopicsTest(unittest.TestCase):
    def setUp(self):
        reset_cache()

    def tearDown(self):
        reset_cache()

    def test_topics_returns_all_when_no_name(self):
        cached.inv = type(
            "MockInv",
            (),
            {
                "topics": {
                    "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                    "shapes": {"parameters": {"targets": {"t2": {"fav": "circle"}}}},
                }
            },
        )()

        result = topics()
        self.assertIn("colours", result)
        self.assertIn("shapes", result)
        self.assertEqual(
            result["colours"]["parameters"]["targets"]["t1"]["fav"], "blue"
        )

    def test_topics_returns_specific_topic(self):
        cached.inv = type(
            "MockInv",
            (),
            {
                "topics": {
                    "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                }
            },
        )()

        result = topics("colours")
        self.assertEqual(result["parameters"]["targets"]["t1"]["fav"], "blue")

    def test_topics_returns_empty_for_missing_topic(self):
        cached.inv = type("MockInv", (), {"topics": {}})()

        result = topics("nonexistent")
        self.assertEqual(result, {"parameters": {"targets": {}}})

    def test_topics_returns_empty_when_inv_has_no_topics_attr(self):
        cached.inv = type("MockInv", (), {})()

        result = topics("anything")
        self.assertEqual(result, {"parameters": {"targets": {}}})

    def test_topics_returns_empty_when_topics_is_none(self):
        cached.inv = type("MockInv", (), {"topics": None})()

        result = topics("anything")
        self.assertEqual(result, {"parameters": {"targets": {}}})

    def test_topics_name_empty_string_returns_all(self):
        cached.inv = type(
            "MockInv",
            (),
            {
                "topics": {
                    "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                }
            },
        )()

        result = topics("")
        self.assertIn("colours", result)
