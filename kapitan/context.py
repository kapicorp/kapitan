#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Explicit compile context for Kapitan.

Provides a ``CompileContext`` dataclass that carries all runtime state previously
held in ``kapitan.cached`` module-level globals.  A ``contextvars.ContextVar``
backs the "current" context so that concurrent threads and asyncio tasks each see
their own isolated state.

Usage::

    from kapitan.context import (
        CompileContext,
        set_current_context,
        current_context,
        reset_context,
    )

    ctx = CompileContext()
    token = set_current_context(ctx)
    try:
        ...  # code that calls current_context()
    finally:
        reset_context(token)
"""

import contextvars
from argparse import Namespace
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CompileContext:
    """Carries all mutable runtime state for a single Kapitan compilation run."""

    # Parsed CLI / programmatic arguments
    args: Namespace = field(default_factory=Namespace)

    # Inventory caches
    inv: dict[str, Any] = field(default_factory=dict)
    global_inv: dict[str, Any] = field(default_factory=dict)
    inventory_global_kadet: dict[str, Any] = field(default_factory=dict)
    inv_cache: dict[str, Any] = field(default_factory=dict)
    inv_sources: set[str] = field(default_factory=set)

    # Secret backend handlers
    gpg_obj: Any = None
    gkms_obj: Any = None
    awskms_obj: Any = None
    azkms_obj: Any = None

    # Core control objects
    dot_kapitan: dict[str, Any] = field(default_factory=dict)
    ref_controller_obj: Any = None
    revealer_obj: Any = None

    # Kadet input cache
    kapitan_input_kadet: Any = None


# Module-level ContextVar — each thread / asyncio task inherits a snapshot of
# the parent's context, so mutations inside a thread do not affect the parent.
_current_context: contextvars.ContextVar[Optional[CompileContext]] = (
    contextvars.ContextVar("kapitan_current_context", default=None)
)


def set_current_context(ctx: CompileContext) -> contextvars.Token:
    """Make *ctx* the active ``CompileContext`` for the current thread/task.

    Returns the token needed to restore the previous context via
    :func:`reset_context`.
    """
    return _current_context.set(ctx)


def current_context() -> Optional[CompileContext]:
    """Return the active ``CompileContext``, or ``None`` if none is set."""
    return _current_context.get()


def reset_context(token: contextvars.Token) -> None:
    """Restore the context that was active before the matching :func:`set_current_context` call."""
    _current_context.reset(token)
