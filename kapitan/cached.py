#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"cached module"

inv = {}
inv_cache = {}
gpg_obj = None
gkms_obj = None
awskms_obj = None
azkms_obj = None
dot_kapitan = {}
ref_controller_obj = None
revealer_obj = None
args = {}  # args won't need resetting
inv_sources = set()


def reset_cache():
    global inv, inv_cache, gpg_obj, gkms_obj, awskms_obj, azkms_obj, dot_kapitan, ref_controller_obj, revealer_obj, inv_sources

    inv = {}
    inv_cache = {}
    inv_sources = set()
    gpg_obj = None
    gkms_obj = None
    awskms_obj = None
    azkms_obj = None
    dot_kapitan = {}
    ref_controller_obj = None
    revealer_obj = None


def from_dict(cache_dict):
    global inv, inv_cache, gpg_obj, gkms_obj, awskms_obj, azkms_obj, dot_kapitan, ref_controller_obj, revealer_obj, inv_sources, args

    inv = cache_dict["inv"]
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


def as_dict():
    return {
        "inv": inv,
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


def reset_inv():
    """clears the inv while fetching remote inventories"""
    global inv
    inv = {}
