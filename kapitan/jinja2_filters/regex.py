#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Regex filters for Jinja2."""

import re

from kapitan.errors import CompileError


def regex_replace(value="", pattern="", replacement="", ignorecase=False):
    """Perform a `re.sub` returning a string"""
    if ignorecase:
        flags = re.IGNORECASE
    else:
        flags = 0
    _re = re.compile(pattern, flags=flags)
    return _re.sub(replacement, value)


def regex_escape(string):
    """Escape all regular expressions special characters from STRING."""
    return re.escape(string)


def regex_search(value, regex, *args, **kwargs):
    """Perform re.search and return the list of matches or a backref"""
    groups = list()
    for arg in args:
        if arg.startswith("\\g"):
            match = re.match(r"\\g<(\S+)>", arg).group(1)
            groups.append(match)
        elif arg.startswith("\\"):
            match = int(re.match(r"\\(\d+)", arg).group(1))
            groups.append(match)
        else:
            raise CompileError("Unknown argument")

    flags = 0
    if kwargs.get("ignorecase"):
        flags |= re.IGNORECASE
    if kwargs.get("multiline"):
        flags |= re.MULTILINE

    match = re.search(regex, value, flags)
    if match:
        if not groups:
            return match.group()
        items = list()
        for item in groups:
            items.append(match.group(item))
        return items


def regex_findall(value, regex, multiline=False, ignorecase=False):
    """Perform re.findall and return the list of matches"""
    flags = 0
    if ignorecase:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    return re.findall(regex, value, flags)
