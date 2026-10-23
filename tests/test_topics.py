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
from kapitan.errors import CompileError
from kapitan.topics import (
    consumed_topics_digest,
    current_target,
    topics,
)


def _mock_inv(topics_data: dict, consumed: dict[str, set[str]] | None = None):
    """Build a stand-in for ``cached.inv`` that mimics the bits topics() uses.

    ``topics_data`` is the aggregated view ``{name: {"parameters": {"targets": ...}}}``.
    ``consumed`` maps target_name -> set of declared consume topic names.
    """
    consumed = consumed or {}

    class MockInv:
        topics = topics_data

        def consumed_topics(self, target):
            return consumed.get(target, set())

    return MockInv()


@pytest.mark.usefixtures("reset_cached_args")
class TopicsTest(unittest.TestCase):
    def setUp(self):
        reset_cache()
        # ContextVars persist across tests within a thread. Clear explicitly so
        # one test setting a calling target doesn't leak into the next.
        self._cv_token = current_target.set(None)

    def tearDown(self):
        current_target.reset(self._cv_token)
        reset_cache()

    def test_topics_returns_all_when_no_name(self):
        cached.inv = _mock_inv(
            {
                "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                "shapes": {"parameters": {"targets": {"t2": {"fav": "circle"}}}},
            }
        )

        result = topics()
        self.assertIn("colours", result)
        self.assertIn("shapes", result)
        self.assertEqual(
            result["colours"]["parameters"]["targets"]["t1"]["fav"], "blue"
        )

    def test_topics_returns_specific_topic(self):
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}}
        )

        result = topics("colours")
        self.assertEqual(result["parameters"]["targets"]["t1"]["fav"], "blue")

    def test_topics_returns_empty_for_missing_topic(self):
        cached.inv = _mock_inv({})

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
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}}
        )

        result = topics("")
        self.assertIn("colours", result)

    # --- consume declaration enforcement -------------------------------------

    def test_topics_raises_when_target_did_not_declare_consume(self):
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}},
            consumed={"consumer": set()},
        )
        with self.assertRaises(CompileError) as ctx:
            topics("colours", target="consumer")
        self.assertIn("consumer", str(ctx.exception))
        self.assertIn("topics.colours.consume: true", str(ctx.exception))

    def test_topics_succeeds_when_target_declared_consume(self):
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}},
            consumed={"consumer": {"colours"}},
        )
        result = topics("colours", target="consumer")
        self.assertEqual(result["parameters"]["targets"]["t1"]["fav"], "blue")

    def test_topics_no_name_raises_listing_undeclared(self):
        cached.inv = _mock_inv(
            {
                "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                "shapes": {"parameters": {"targets": {"t2": {"fav": "circle"}}}},
            },
            consumed={"consumer": {"colours"}},
        )
        with self.assertRaises(CompileError) as ctx:
            topics(target="consumer")
        msg = str(ctx.exception)
        self.assertIn("topics.shapes.consume: true", msg)
        # ``colours`` is declared so it must not appear in the hint
        self.assertNotIn("topics.colours.consume: true", msg)

    def test_topics_no_name_succeeds_when_all_declared(self):
        cached.inv = _mock_inv(
            {
                "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                "shapes": {"parameters": {"targets": {"t2": {"fav": "circle"}}}},
            },
            consumed={"consumer": {"colours", "shapes"}},
        )
        result = topics(target="consumer")
        self.assertIn("colours", result)
        self.assertIn("shapes", result)

    def test_topics_no_name_passes_when_inventory_has_no_topics(self):
        cached.inv = _mock_inv({}, consumed={"consumer": set()})
        # Vacuously: every topic that would be returned is declared.
        self.assertEqual(topics(target="consumer"), {})

    def test_topics_uses_contextvar_when_no_target_arg(self):
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}},
            consumed={"consumer": set()},
        )
        current_target.set("consumer")
        with self.assertRaises(CompileError):
            topics("colours")

    def test_topics_skips_check_outside_compile_context(self):
        # No target arg, no ContextVar set — e.g. ``kapitan inventory --topics``.
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}},
            consumed={},
        )
        # Should not raise even though no target ever declared ``colours``.
        result = topics()
        self.assertIn("colours", result)


@pytest.mark.usefixtures("reset_cached_args")
class ConsumedTopicsDigestTest(unittest.TestCase):
    def setUp(self):
        reset_cache()

    def tearDown(self):
        reset_cache()

    def test_returns_none_when_target_declares_no_consumes(self):
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}},
            consumed={"consumer": set()},
        )
        self.assertIsNone(consumed_topics_digest("consumer"))

    def test_digest_changes_when_producer_params_change(self):
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}}},
            consumed={"consumer": {"colours"}},
        )
        before = consumed_topics_digest("consumer")

        # Producer flips its topic parameter — consumer's digest must move.
        cached.inv = _mock_inv(
            {"colours": {"parameters": {"targets": {"t1": {"fav": "red"}}}}},
            consumed={"consumer": {"colours"}},
        )
        after = consumed_topics_digest("consumer")

        self.assertIsNotNone(before)
        self.assertNotEqual(before, after)

    def test_digest_stable_when_unrelated_topic_changes(self):
        # Consumer only declared ``colours``; mutating ``shapes`` must not move
        # the digest — that's the whole point of the explicit declaration.
        cached.inv = _mock_inv(
            {
                "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                "shapes": {"parameters": {"targets": {"t2": {"fav": "circle"}}}},
            },
            consumed={"consumer": {"colours"}},
        )
        before = consumed_topics_digest("consumer")

        cached.inv = _mock_inv(
            {
                "colours": {"parameters": {"targets": {"t1": {"fav": "blue"}}}},
                "shapes": {"parameters": {"targets": {"t2": {"fav": "square"}}}},
            },
            consumed={"consumer": {"colours"}},
        )
        after = consumed_topics_digest("consumer")

        self.assertEqual(before, after)
