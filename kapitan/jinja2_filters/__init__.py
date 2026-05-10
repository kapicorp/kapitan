#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Jinja2 filters for Kapitan.

This package re-exports everything that was previously in the flat
kapitan/jinja2_filters.py for backward compatibility.
"""

import logging
import os
import types
from importlib import util

from kapitan import defaults
from kapitan.jinja2_filters.datetime_filters import strftime, to_datetime
from kapitan.jinja2_filters.encoding import base64_decode, base64_encode
from kapitan.jinja2_filters.regex import (
    regex_escape,
    regex_findall,
    regex_replace,
    regex_search,
)
from kapitan.jinja2_filters.reveal import reveal_maybe
from kapitan.jinja2_filters.serialization import (
    fileglob,
    merge_strategic,
    randomize_list,
    ternary,
    to_bool,
    to_toml,
    to_yaml,
)
from kapitan.utils.hashing import sha256_string


logger = logging.getLogger(__name__)


def _jinja_error_info(trace_data):
    """Extract jinja2 templating related frames from traceback data"""
    try:
        return [
            x
            for x in trace_data
            if x[2] in ("top-level template code", "template", "<module>")
        ][-1]
    except IndexError:
        pass


def load_jinja2_filters(env):
    """Load Jinja2 custom filters into env"""
    env.filters["sha256"] = sha256_string
    env.filters["b64encode"] = base64_encode
    env.filters["b64decode"] = base64_decode
    env.filters["yaml"] = to_yaml
    env.filters["toml"] = to_toml
    env.filters["fileglob"] = fileglob
    env.filters["bool"] = to_bool
    env.filters["to_datetime"] = to_datetime
    env.filters["strftime"] = strftime
    env.filters["regex_replace"] = regex_replace
    env.filters["regex_escape"] = regex_escape
    env.filters["regex_search"] = regex_search
    env.filters["regex_findall"] = regex_findall
    env.filters["reveal_maybe"] = reveal_maybe
    env.filters["ternary"] = ternary
    env.filters["shuffle"] = randomize_list
    env.filters["merge_strategic"] = merge_strategic


def load_module_from_path(env, path):
    """
    Loads a python module from provided path and adds it to jinja2 environment.
    Filter name is same as that of function.
    """
    try:
        module_name = os.path.basename(path).split(".")[0]
        custom_filter_spec = util.spec_from_file_location(module_name, path)
        custom_filter_module = util.module_from_spec(custom_filter_spec)
        custom_filter_spec.loader.exec_module(custom_filter_module)
        for function in dir(custom_filter_module):
            if isinstance(getattr(custom_filter_module, function), types.FunctionType):
                logger.debug("custom filter loaded from %s", path)
                env.filters[function] = getattr(custom_filter_module, function)
    except Exception as e:
        raise OSError(
            f"jinja2 failed to render, could not load filter at {path}: {e}"
        ) from e
        logger.debug("failed to find custom filter from path %s", path)


def load_jinja2_filters_from_file(env, jinja2_filters):
    """
    If filter points to default file and in case it doesn't exist then proceed silently, no error.
    Otherwise try to load module (which will throw error in case of non existence of file).
    """
    jinja2_filters = os.path.normpath(jinja2_filters)
    if jinja2_filters == defaults.DEFAULT_JINJA2_FILTERS_PATH:
        if not os.path.isfile(jinja2_filters):
            return
    load_module_from_path(env, jinja2_filters)
