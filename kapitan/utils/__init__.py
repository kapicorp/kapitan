#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Utilities for Kapitan.

This package re-exports everything that was previously in the flat kapitan/utils.py
for backward compatibility, while organising code into domain submodules.
"""

import collections
import logging
import sys

import yaml

from kapitan import cached
from kapitan.utils.archive import (
    SafeCopyError,
    copy_tree,
    force_copy_file,
    make_request,
    safe_copy_file,
    safe_copy_tree,
    unpack_downloaded_file,
)
from kapitan.utils.dotkapitan import dot_kapitan_config, from_dot_kapitan
from kapitan.utils.hashing import (
    dictionary_hash,
    directory_hash,
    get_entropy,
    sha256_string,
)
from kapitan.utils.paths import (
    file_mode,
    list_all_paths,
    normalise_join_path,
    search_target_token_paths,
)
from kapitan.utils.rendering import (
    render_jinja2,
    render_jinja2_file,
    render_jinja2_template,
)
from kapitan.utils.version import (
    check_version,
    compare_versions,
    termcolor,
)


logger = logging.getLogger(__name__)


try:
    from enum import StrEnum
except ImportError:
    from strenum import StrEnum

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader


def fatal_error(message):
    "Logs error message, sys.exit(1)"
    logger.error(message)
    sys.exit(1)


def prune_empty(d):
    """
    Remove empty lists and empty dictionaries from d
    (similar to jsonnet std.prune but faster)
    """
    if not isinstance(d, dict | list):
        return d

    if isinstance(d, list):
        if len(d) > 0:
            return [v for v in (prune_empty(v) for v in d) if v is not None]

    if isinstance(d, dict):
        if len(d) > 0:
            return {
                k: v
                for k, v in ((k, prune_empty(v)) for k, v in d.items())
                if v is not None
            }


class PrettyDumper(yaml.SafeDumper):
    """
    Increases indent of nested lists.
    By default, they are indented at the same level as the key on the previous line.
    More info on https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation
    """

    def increase_indent(self, flow=False, indentless=False):
        return super(PrettyDumper, self).increase_indent(flow, False)

    @classmethod
    def get_dumper_for_style(cls, style_selection="double-quotes"):
        cls.add_representer(
            str,
            __import__("functools").partial(
                multiline_str_presenter, style_selection=style_selection
            ),
        )
        return cls


def multiline_str_presenter(dumper, data, style_selection="double-quotes"):
    """
    Configures yaml for dumping multiline strings with given style.
    By default, strings are getting dumped with style='"'.
    Ref: https://github.com/yaml/pyyaml/issues/240#issuecomment-1018712495
    """
    supported_styles = {"literal": "|", "folded": ">", "double-quotes": '"'}
    style = supported_styles.get(style_selection)

    if data.count("\n") > 0:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def null_presenter(dumper, data):
    """Configures yaml for omitting value from null-datatype"""
    flag_value = False
    if hasattr(cached.args, "yaml_dump_null_as_empty"):
        flag_value = cached.args.yaml_dump_null_as_empty

    if flag_value:
        return dumper.represent_scalar("tag:yaml.org,2002:null", "")
    return dumper.represent_scalar("tag:yaml.org,2002:null", "null")


PrettyDumper.add_representer(type(None), null_presenter)


def flatten_dict(d, parent_key="", sep="."):
    """Flatten nested elements in a dictionary"""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.abc.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def deep_get(dictionary, keys, previousKey=None):
    """Search recursively for 'keys' in 'dictionary' and return value, otherwise return None"""
    value = None
    if len(keys) > 0:
        value = dictionary.get(keys[0], None) if isinstance(dictionary, dict) else None

        if value:
            if len(keys) == 1:
                return value

            if not isinstance(value, dict):
                return None

            return deep_get(value, keys[1:], previousKey=keys[0])
        if isinstance(dictionary, dict):
            if "*" in keys[0]:
                key_lower = keys[0].replace("*", "").lower()
                for dict_key in dictionary:
                    if key_lower in dict_key.lower():
                        if len(keys) == 1:
                            return dictionary[dict_key]
                        return deep_get(
                            dictionary[dict_key], keys[1:], previousKey=keys[0]
                        )

            if not previousKey:
                for v in dictionary.values():
                    if isinstance(v, dict):
                        item = None
                        if len(keys) > 1:
                            item = deep_get(v, keys, previousKey=keys[0])
                        else:
                            item = deep_get(v, keys)

                        if item is not None:
                            return item

    return value


def searchvar(args):
    """Show all inventory files where a given reclass variable is declared"""
    output = []
    maxlength = 0
    keys = args.searchvar.split(".")
    for full_path in list_all_paths(args.inventory_path):
        if full_path.endswith((".yml", ".yaml")):
            with open(full_path) as fd:
                data = yaml.load(fd, Loader=YamlLoader)
                value = deep_get(data, keys)
                if value is not None:
                    output.append((full_path, value))
                    maxlength = max(len(full_path), maxlength)
    if args.pretty_print:
        for i in output:
            print(i[0])
            for line in yaml.dump(i[1], default_flow_style=False).splitlines():
                print("    ", line)
            print()
    else:
        for i in output:
            print("{0!s:{length}} {1!s}".format(*i, length=maxlength + 2))
