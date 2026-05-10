#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Base64 encoding/decoding filters for Jinja2."""

import base64


def base64_encode(string):
    return base64.b64encode(string.encode("UTF-8")).decode("UTF-8")


def base64_decode(string):
    return base64.b64decode(string).decode("UTF-8")
