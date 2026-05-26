#!/usr/bin/env python3

# Copyright 2026 The Kapitan Authors
# SPDX-FileCopyrightText: 2024 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Topics: cross-target parameter aggregation.

Targets opt into a topic by declaring parameters under
``parameters.kapitan.topics.<name>.parameters``. Kapitan aggregates each
participating target's topic parameters into a single view of shape::

    {"parameters": {"targets": {<target_name>: <topic_parameters>, ...}}}

This module exposes a single :func:`topics` accessor that is independent of any
particular input type (kadet, jinja2, jsonnet, ...).
"""

from kapitan import cached


# Empty, well-shaped result returned when a requested topic does not exist, so
# callers can iterate ``.parameters.targets`` safely.
_EMPTY_TOPIC: dict = {"parameters": {"targets": {}}}


def topics(name: str | None = None) -> dict:
    """Return aggregated topic parameters across all targets.

    Args:
        name: Topic name. When ``None`` (or empty), returns the full mapping of
            every topic keyed by topic name. When provided, returns the single
            topic view, or an empty well-shaped dict if the topic is unknown.

    Returns:
        Plain ``dict`` data suitable for any input type. Kadet additionally
        wraps the result in a ``kadet.Dict`` for attribute-style access.
    """
    all_topics = getattr(cached.inv, "topics", {}) or {}
    if not name:
        return all_topics
    return all_topics.get(name, dict(_EMPTY_TOPIC))
