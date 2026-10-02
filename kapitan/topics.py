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

Consumers must explicitly declare their intent to read a topic by setting
``parameters.kapitan.topics.<name>.consume: true``. Declaration turns a hidden
cross-target dependency into an explicit one, which is what lets input caches
(see :mod:`kapitan.inputs.cache`) mix producer-side digests into the consumer's
cache key without losing correctness.
"""

import contextvars
import json
from typing import Iterable

from kapitan import cached
from kapitan.errors import CompileError


# Shared across input types so ``topics()`` knows which target is calling it.
# kadet, jinja2, and jsonnet inputs each ``.set()`` this before evaluating user
# code. Default ``None`` means "called outside a compile context" (e.g. the
# ``kapitan inventory --topics`` CLI path), in which case the consume check is
# skipped.
current_target: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "kapitan_current_target", default=None
)

_EMPTY_TOPIC: dict = {"parameters": {"targets": {}}}


def _hint(target: str, names: Iterable[str]) -> str:
    lines = [
        f"  parameters.kapitan.topics.{name}.consume: true" for name in sorted(names)
    ]
    return (
        f"target '{target}' must declare the topic(s) it consumes. Add to its "
        f"inventory:\n" + "\n".join(lines)
    )


def topics(name: str | None = None, target: str | None = None) -> dict:
    """Return aggregated topic parameters across all targets.

    Args:
        name: Topic name. When ``None`` (or empty), returns the full mapping of
            every topic keyed by topic name. When provided, returns the single
            topic view, or an empty well-shaped dict if the topic is unknown.
        target: Calling target name. Defaults to the value of the
            :data:`current_target` ContextVar, which input types set before
            evaluating user code. When neither is set (outside a compile
            context — e.g. the ``kapitan inventory --topics`` CLI path) the
            consume check is skipped.

    Raises:
        CompileError: When called from a target that has not declared the
            requested topic(s) under ``kapitan.topics.<name>.consume: true``.
            For ``topics()`` with no name, every topic that would be returned
            must be declared, else the error lists the undeclared ones.

    Returns:
        Plain ``dict`` data suitable for any input type. Kadet additionally
        wraps the result in a ``kadet.Dict`` for attribute-style access.
    """
    all_topics = getattr(cached.inv, "topics", {}) or {}

    if target is None:
        target = current_target.get()

    if target is not None:
        declared = _declared_for(target)
        if name:
            if name not in declared:
                raise CompileError(_hint(target, [name]))
        else:
            undeclared = set(all_topics) - declared
            if undeclared:
                raise CompileError(_hint(target, undeclared))

    if not name:
        return all_topics
    return all_topics.get(name, dict(_EMPTY_TOPIC))


def _declared_for(target: str) -> set[str]:
    """Topics that ``target`` has declared ``consume: true`` on.

    Wraps :meth:`Inventory.consumed_topics` so callers do not need to know
    about the inventory object shape — and so unit tests can mock the
    inventory with a minimal stand-in.
    """
    consumed = getattr(cached.inv, "consumed_topics", None)
    if callable(consumed):
        return consumed(target)
    return set()


def consumed_topics_digest(target: str) -> bytes | None:
    """Stable digest over the topic views ``target`` declared as consumed.

    Returns ``None`` when the target has declared no consumes — callers should
    skip mixing into their cache key in that case, so targets that never use
    topics keep their pre-existing cache keys.

    The digest folds in topic *name* and aggregated *value* together so a
    rename of an unrelated topic doesn't perturb this target's key, but any
    producer-side change to a consumed topic does.
    """
    # Local import to avoid a cycle: inputs.cache → topics is the only direction.
    from kapitan.inputs.cache import InputCache

    declared = _declared_for(target)
    if not declared:
        return None

    all_topics = getattr(cached.inv, "topics", {}) or {}
    h = InputCache.hash_object()
    for name in sorted(declared):
        topic_view = all_topics.get(name, dict(_EMPTY_TOPIC))
        rep = json.dumps(topic_view, sort_keys=True, default=str)
        h.update(name.encode("utf-8"))
        h.update(b"\x00")  # separator so "ab" + "c" doesn't collide with "a" + "bc"
        h.update(rep.encode("utf-8"))
        h.update(b"\x00")
    return h.digest()
