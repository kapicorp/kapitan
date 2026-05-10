#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Serialization and data-structure filters for Jinja2."""

import glob
import os
from random import Random, shuffle

import toml
import yaml
from six import string_types


def to_yaml(obj):
    return yaml.safe_dump(obj, default_flow_style=False)


def to_toml(obj):
    return toml.dumps(obj)


def fileglob(pathname):
    """Return list of matched regular files for glob."""
    return [g for g in glob.glob(pathname) if os.path.isfile(g)]


def to_bool(a):
    """Return a bool for the arg."""
    if a is None or isinstance(a, bool):
        return a
    if isinstance(a, string_types):
        a = a.lower()
    if a in ("yes", "on", "1", "true", 1):
        return True
    return False


def ternary(value, true_val, false_val, none_val=None):
    """value ? true_val : false_val"""
    if value is None and none_val is not None:
        return none_val
    if bool(value):
        return true_val
    return false_val


def randomize_list(mylist, seed=None):
    try:
        mylist = list(mylist)
        if seed:
            r = Random(seed)
            r.shuffle(mylist)
        else:
            shuffle(mylist)
    except Exception:
        pass
    return mylist


def merge_strategic(data):
    """
    Recursively traverse the input data structure.
    - If encountering a list of dicts each with a 'name' key, merge them by name.
    - Process nested dictionaries and lists recursively.
    """
    if not isinstance(data, list | dict):
        return data

    if isinstance(data, list):
        processed_list = [merge_strategic(item) for item in data]

        if all(isinstance(item, dict) and "name" in item for item in processed_list):
            merged = {}
            for item in processed_list:
                key = item["name"]
                if key not in merged:
                    merged[key] = {}
                merged[key].update(item)
            return list(merged.values())
        return processed_list

    if isinstance(data, dict):
        return {key: merge_strategic(value) for key, value in data.items()}
