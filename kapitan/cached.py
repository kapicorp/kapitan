#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Global cache for Kapitan's runtime state.

This module maintains global state for inventory, secrets handlers, and other
objects that need to be shared across Kapitan's execution.
"""

from argparse import Namespace
from typing import Any


# Inventory caches
inv: dict[str, Any] = {}
global_inv: dict[str, Any] = {}
inventory_global_kadet: dict[str, Any] = {}
inv_cache: dict[str, Any] = {}

# Secrets handlers
# gkms/awskms/azkms clients are memoized in their own modules via
# functools.cache (flushed through the clearer registry below); gpg remains here.
gpg_obj: Any = None

# Configuration and control objects
dot_kapitan: dict[str, Any] = {}
ref_controller_obj: Any = None
revealer_obj: Any = None
args: Namespace = Namespace()  # args won't need resetting
inv_sources: set[str] = set()

# Kadet caches
kapitan_input_kadet = None

# Memoized secret-handler factories register their ``cache_clear`` here so
# ``reset_cache`` can flush them without importing the optional cloud SDK
# modules. Populated lazily as each refs.secrets.* module is imported.
_handler_cache_clearers: list = []


def register_handler_cache_clearer(clear_fn) -> None:
    """Register a callable that clears a memoized secret-handler factory cache."""
    _handler_cache_clearers.append(clear_fn)


def reset_cache():
    global \
        inv, \
        global_inv, \
        inv_cache, \
        gpg_obj, \
        dot_kapitan, \
        ref_controller_obj, \
        revealer_obj, \
        inv_sources

    inv = {}
    global_inv = {}
    inv_cache = {}
    inv_sources = set()
    gpg_obj = None
    dot_kapitan = {}
    ref_controller_obj = None
    revealer_obj = None

    # flush memoized secret-handler factories (lru_cache stores)
    for clear_fn in _handler_cache_clearers:
        clear_fn()


def from_dict(cache_dict: dict[str, Any]) -> None:
    """
    Restore cache state from a dictionary.

    Args:
        cache_dict: Dictionary containing serialized cache state
    """
    global \
        inv, \
        global_inv, \
        inv_cache, \
        gpg_obj, \
        dot_kapitan, \
        ref_controller_obj, \
        revealer_obj, \
        inv_sources, \
        args

    inv = cache_dict["inv"]
    global_inv = cache_dict["global_inv"]
    inv_cache = cache_dict["inv_cache"]
    inv_sources = cache_dict["inv_sources"]
    gpg_obj = cache_dict["gpg_obj"]
    dot_kapitan = cache_dict["dot_kapitan"]
    ref_controller_obj = cache_dict["ref_controller_obj"]
    revealer_obj = cache_dict["revealer_obj"]
    args = cache_dict["args"]


def as_dict() -> dict[str, Any]:
    """
    Serialize cache state to a dictionary.

    Returns:
        Dictionary containing all cache variables
    """
    return {
        "inv": inv,
        "global_inv": global_inv,
        "inv_cache": inv_cache,
        "inv_sources": inv_sources,
        "gpg_obj": gpg_obj,
        "dot_kapitan": dot_kapitan,
        "ref_controller_obj": ref_controller_obj,
        "revealer_obj": revealer_obj,
        "args": args,
    }


def reset_inv() -> None:
    """Clear the inventory cache while fetching remote inventories."""
    global inv
    inv = {}
