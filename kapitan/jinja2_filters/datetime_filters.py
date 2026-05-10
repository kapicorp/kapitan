#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Date/time filters for Jinja2.

Named `datetime_filters` to avoid shadowing the stdlib `datetime` module.
"""

import datetime
import time

from kapitan.errors import CompileError


def to_datetime(string, format="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(string, format)


def strftime(string_format, second=None):
    """Return current date string for format.

    See https://docs.python.org/3/library/time.html#time.strftime for format.
    """
    if second is not None:
        try:
            second = int(second)
        except Exception as e:
            raise CompileError(f"Invalid value for epoch value ({second})") from e
    return time.strftime(string_format, time.localtime(second))
