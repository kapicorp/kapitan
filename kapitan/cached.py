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
dot_kapitan = {}
ref_controller_obj = None
revealer_obj = None
args = {}  # args won't need resetting
inv_sources = set()


def reset_cache():
    global inv, inv_cache, gpg_obj, gkms_obj, awskms_obj, dot_kapitan, ref_controller_obj, revealer_obj, inv_sources

    inv = {}
    inv_cache = {}
    inv_sources = set()
    gpg_obj = None
    gkms_obj = None
    awskms_obj = None
    dot_kapitan = {}
    ref_controller_obj = None
    revealer_obj = None


def reset_inv():
    """clears the inv while fetching remote inventories"""
    global inv
    inv = {}
