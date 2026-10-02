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
gpg_obj: Any = None
gkms_obj: Any = None
awskms_obj: Any = None
azkms_obj: Any = None

# Configuration and control objects
dot_kapitan: dict[str, Any] = {}
ref_controller_obj: Any = None
revealer_obj: Any = None
args: Namespace = Namespace()  # args won't need resetting
inv_sources: set[str] = set()

# Kadet caches
kapitan_input_kadet = None

# Helm cache: rendered manifests keyed on (chart_dir content, helm_values,
# helm_params, helm_path). Lets HelmChart() callers skip the helm subprocess
# even when their kadet cache misses (e.g. when an unrelated inventory key
# changed but helm-relevant inputs did not).
kapitan_input_helm = None

# Shared cache metrics for the compile pool, keyed by input_type_name.
# Populated by compile_targets() only when caching is enabled, then propagated
# to workers via the pool initializer so every InputCache(input_type_name=N)
# bumps the same shared CacheMetrics across processes.
input_cache_metrics: dict | None = None


def reset_cache():
    global \
        inv, \
        global_inv, \
        inv_cache, \
        gpg_obj, \
        gkms_obj, \
        awskms_obj, \
        azkms_obj, \
        dot_kapitan, \
        ref_controller_obj, \
        revealer_obj, \
        inv_sources

    inv = {}
    global_inv = {}
    inv_cache = {}
    inv_sources = set()
    gpg_obj = None
    gkms_obj = None
    awskms_obj = None
    azkms_obj = None
    dot_kapitan = {}
    ref_controller_obj = None
    revealer_obj = None


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
        gkms_obj, \
        awskms_obj, \
        azkms_obj, \
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
    gkms_obj = cache_dict["gkms_obj"]
    awskms_obj = cache_dict["awskms_obj"]
    azkms_obj = cache_dict["azkms_obj"]
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
        "gkms_obj": gkms_obj,
        "awskms_obj": awskms_obj,
        "azkms_obj": azkms_obj,
        "dot_kapitan": dot_kapitan,
        "ref_controller_obj": ref_controller_obj,
        "revealer_obj": revealer_obj,
        "args": args,
    }


def reset_inv() -> None:
    """Clear the inventory cache while fetching remote inventories."""
    global inv
    inv = {}
