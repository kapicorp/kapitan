#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
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


def reset_cache():
    global inv, inv_cache, gpg_obj, gkms_obj, awskms_obj, dot_kapitan, ref_controller_obj, revealer_obj
    inv = {}
    inv_cache = {}
    gpg_obj = None
    gkms_obj = None
    awskms_obj = None
    dot_kapitan = {}
    ref_controller_obj = None
    revealer_obj = None
