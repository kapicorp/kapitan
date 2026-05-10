#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Reveal filter for Jinja2 — the only filter that accesses kapitan.cached."""

from kapitan import cached


def reveal_maybe(ref_tag):
    "Will reveal ref_tag if valid and --reveal flag is used"
    if cached.args.reveal:
        return cached.revealer_obj.reveal_raw(ref_tag)
    return ref_tag
