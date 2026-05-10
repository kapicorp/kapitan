#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Backward-compatible proxy for Kapitan's runtime state.

Module-level attribute reads and writes are transparently routed through the
active ``CompileContext`` (set via :func:`kapitan.context.set_current_context`)
when one is present.  When no context is active the legacy fallback dict is used,
preserving full backward compatibility.

New code should use ``CompileContext`` directly via ``kapitan.context``.
"""

import sys
import types
from argparse import Namespace
from typing import Any


# ---------------------------------------------------------------------------
# Fields that proxy to the active CompileContext when one is set
# ---------------------------------------------------------------------------
_CONTEXT_FIELDS: frozenset[str] = frozenset(
    {
        "inv",
        "global_inv",
        "inventory_global_kadet",
        "inv_cache",
        "inv_sources",
        "gpg_obj",
        "gkms_obj",
        "awskms_obj",
        "azkms_obj",
        "dot_kapitan",
        "ref_controller_obj",
        "revealer_obj",
        "args",
        "kapitan_input_kadet",
    }
)

# ---------------------------------------------------------------------------
# Fallback store — used when no CompileContext is active (legacy / CLI mode)
# All functions operate on this dict directly to avoid ``global`` statements.
# ---------------------------------------------------------------------------
_fallback: dict[str, Any] = {
    "inv": {},
    "global_inv": {},
    "inventory_global_kadet": {},
    "inv_cache": {},
    "inv_sources": set(),
    "gpg_obj": None,
    "gkms_obj": None,
    "awskms_obj": None,
    "azkms_obj": None,
    "dot_kapitan": {},
    "ref_controller_obj": None,
    "revealer_obj": None,
    "args": Namespace(),
    "kapitan_input_kadet": None,
}


def reset_cache() -> None:
    """Reset all fallback cache state to defaults.

    In legacy mode (no active ``CompileContext``) this restores the module
    globals.  It does *not* affect any active ``CompileContext``; create a new
    ``CompileContext`` instance for a clean slate in new code instead.
    """
    _fallback["inv"] = {}
    _fallback["global_inv"] = {}
    _fallback["inv_cache"] = {}
    _fallback["inv_sources"] = set()
    _fallback["gpg_obj"] = None
    _fallback["gkms_obj"] = None
    _fallback["awskms_obj"] = None
    _fallback["azkms_obj"] = None
    _fallback["dot_kapitan"] = {}
    _fallback["ref_controller_obj"] = None
    _fallback["revealer_obj"] = None


def from_dict(cache_dict: dict[str, Any]) -> None:
    """Restore fallback cache state from a dictionary."""
    for key in (
        "inv",
        "global_inv",
        "inv_cache",
        "inv_sources",
        "gpg_obj",
        "gkms_obj",
        "awskms_obj",
        "azkms_obj",
        "dot_kapitan",
        "ref_controller_obj",
        "revealer_obj",
        "args",
    ):
        _fallback[key] = cache_dict[key]


def as_dict() -> dict[str, Any]:
    """Serialize current fallback cache state to a dictionary."""
    return {
        "inv": _fallback["inv"],
        "global_inv": _fallback["global_inv"],
        "inv_cache": _fallback["inv_cache"],
        "inv_sources": _fallback["inv_sources"],
        "gpg_obj": _fallback["gpg_obj"],
        "gkms_obj": _fallback["gkms_obj"],
        "awskms_obj": _fallback["awskms_obj"],
        "azkms_obj": _fallback["azkms_obj"],
        "dot_kapitan": _fallback["dot_kapitan"],
        "ref_controller_obj": _fallback["ref_controller_obj"],
        "revealer_obj": _fallback["revealer_obj"],
        "args": _fallback["args"],
    }


def reset_inv() -> None:
    """Clear the inventory cache (used when fetching remote inventories)."""
    _fallback["inv"] = {}


# ---------------------------------------------------------------------------
# Module proxy — intercepts attribute access to route through CompileContext
# ---------------------------------------------------------------------------


class _CachedModule(types.ModuleType):
    """Proxy that routes proxied attributes through the active CompileContext."""

    def __getattribute__(self, name: str) -> Any:
        if name in _CONTEXT_FIELDS:
            from kapitan.context import current_context

            ctx = current_context()
            if ctx is not None:
                return getattr(ctx, name)
            return _fallback[name]
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in _CONTEXT_FIELDS:
            from kapitan.context import current_context

            ctx = current_context()
            if ctx is not None:
                setattr(ctx, name, value)
                return
            _fallback[name] = value
            return
        super().__setattr__(name, value)


# Replace this module in sys.modules with the proxy so that attribute access on
# ``import kapitan.cached`` transparently routes through __getattribute__ /
# __setattr__.  Non-proxied names (functions, constants) are copied into the
# proxy's __dict__ so they remain accessible.
_proxy = _CachedModule(__name__)
_proxy.__dict__.update(
    {k: v for k, v in globals().items() if k not in _CONTEXT_FIELDS and k != "_proxy"}
)
sys.modules[__name__] = _proxy
