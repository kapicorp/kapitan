#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import os
import sys
from typing import Any

import yaml
from omegaconf import Container, ListMergeMode, Node, OmegaConf

logger = logging.getLogger(__name__)


def key(_node_: Node):
    """resolver function, that returns the name of its key"""
    return _node_._key()


def parentkey(_parent_: Node):
    """resolver function, that returns the name of its parent key"""
    return _parent_._key()


def fullkey(_node_: Node):
    """resolver function, that returns the full name of its key"""
    return _node_._get_full_key("")


def access_key_with_dots(*key: str, _root_: Container):
    """resolver function, that accesses a key with dots in it"""
    value = _root_
    for part in key:
        value = value[part]

    return value


def escape_interpolation(content: str):
    """resolver function that escapes an interpolation for the next resolving step"""
    return f"${{{content}}}"


def merge(*args):
    """resolver function, that merges omegaconf objects"""
    return OmegaConf.merge(*args, list_merge_mode=ListMergeMode.EXTEND)


def to_dict(input_list: list):
    """resolver function, that converts an object to a dict"""
    if type(input_list) is not list or OmegaConf.is_list(input_list):
        # warning: input is not list
        return input_list

    if not all([type(item) is list or OmegaConf.is_dict(item) for item in input_list]):
        # warning: some items are not dict
        return input_list

    return {dict_key: item[dict_key] for item in input_list for dict_key in item}


def to_list(input_obj: Any):
    """resolver function, that converts an object to a list"""
    if type(input_obj) is dict or OmegaConf.is_dict(input_obj):
        return [{k: v} for k, v in input_obj.items()]

    return list(input_obj)


def to_yaml(key: str, _root_: Container):
    content = OmegaConf.select(_root_, key)
    return yaml.dump(OmegaConf.to_container(content, resolve=True))


def default(*args):
    output = ""
    for arg in args[:-1]:
        output += "${oc.select:" + str(arg) + ","

    output += str(args[-1])
    output += "}" * (len(args) - 1)
    return output


def relpath(absolute_path: str, _node_: Node):
    """
    resolver function, that translates an absolute yaml-path to its relative path
    """

    node_parts = []
    path_parts = absolute_path.split(".")
    relative_path = ""

    i = 0
    node = _node_
    while node._key() is not None:
        node_parts.append(node._key())
        node = node._get_parent()
        i += 1

    node_parts.reverse()

    for idx, (path_part, node_path) in enumerate(zip(path_parts, node_parts)):
        if not path_part == node_path:
            rel_prefix = "." * (i - idx) if idx != 0 else ""
            relative_path = rel_prefix + ".".join(path_parts[idx:])
            break

    if not relative_path:
        # warning: self reference
        return "SELF REFERENCE DETECTED"

    relative_interpolation = "${" + relative_path + "}"

    return relative_interpolation


def write_to_key(destination: str, origin: str, _root_):
    """
    resolver function to write any content to different place in the inventory
    NOTE: Behavior for lists is not well-defined
    """
    # fetch and resolve content
    try:
        content = OmegaConf.select(_root_, origin)
        if not content:
            # warning: origin could not be found / empty content
            return "NOT FOUND"

        # resolve relative interpolations
        try:
            # replace with OC.to_object(), when it supports escaped interpolations (wip)
            # reference: https://github.com/omry/omegaconf/pull/1113
            config = copy.deepcopy(content)
            OmegaConf.resolve(config, True)
        except Exception as e:
            # resolver error
            logger.warning(e)
            return "ERROR WHILE RESOLVING"

        # remove when issue above is resolved
        OmegaConf.set_readonly(config, False, recursive=True)

        # write resolved content back to _root_
        OmegaConf.update(_root_, destination, config, merge=True, force_add=True)
    except Exception as e:
        raise e
    return "DONE"


def from_file(file_path: str):
    if os.path.isfile(file_path):
        with open(file_path, "r") as f:
            return f.read()
    else:
        logger.error(f"from_file: file {file_path} does not exist")
    return "FILE NOT EXISTS"


def filename(_node_: Node):
    return _node_._get_flag("filename")


def parent_filename(_parent_: Node):
    return _parent_._get_flag("filename")


def path(_node_: Node):
    return _node_._get_flag("path")


def parent_path(_parent_: Node):
    return _parent_._get_flag("path")


def condition_if(condition: str, config: dict):
    if bool(condition):
        return config
    else:
        return {}


def condition_if_else(condition: str, config_if: dict, config_else: dict):
    if bool(condition):
        return config_if
    else:
        return config_else


def condition_not(condition: str):
    return not bool(condition)


def condition_and(*conditions: str):
    return all(conditions)


def condition_or(*conditions: str):
    return any(conditions)


def condition_equal(*configs):
    return all(config == configs[0] for config in configs)


def register_resolvers() -> None:
    """register pre-defined and user-defined resolvers"""
    replace = True

    # yaml key utility functions
    OmegaConf.register_new_resolver("key", key, replace=replace)
    OmegaConf.register_new_resolver("parentkey", parentkey, replace=replace)
    OmegaConf.register_new_resolver("fullkey", fullkey, replace=replace)
    OmegaConf.register_new_resolver("relpath", relpath, replace=replace)

    # yaml object utility functions
    OmegaConf.register_new_resolver("access", access_key_with_dots, replace=replace)
    OmegaConf.register_new_resolver("escape", escape_interpolation, replace=replace)
    OmegaConf.register_new_resolver("merge", merge, replace=replace)
    OmegaConf.register_new_resolver("dict", to_dict, replace=replace)
    OmegaConf.register_new_resolver("list", to_list, replace=replace)
    OmegaConf.register_new_resolver("yaml", to_yaml, replace=replace)
    OmegaConf.register_new_resolver("add", lambda x, y: x + y, replace=replace)
    OmegaConf.register_new_resolver("default", default, replace=replace)
    OmegaConf.register_new_resolver("write", write_to_key, replace=replace)
    OmegaConf.register_new_resolver("from_file", from_file, replace=replace)
    OmegaConf.register_new_resolver("filename", filename, replace=replace)
    OmegaConf.register_new_resolver("parent_filename", parent_filename, replace=replace)
    OmegaConf.register_new_resolver("path", path, replace=replace)
    OmegaConf.register_new_resolver("parent_path", parent_path, replace=replace)

    # boolean algebra
    OmegaConf.register_new_resolver("if", condition_if, replace=replace)
    OmegaConf.register_new_resolver("ifelse", condition_if_else, replace=replace)
    OmegaConf.register_new_resolver("and", condition_and, replace=replace)
    OmegaConf.register_new_resolver("or", condition_or, replace=replace)
    OmegaConf.register_new_resolver("not", condition_not, replace=replace)
    OmegaConf.register_new_resolver("equal", condition_equal, replace=replace)

    # user defined resolvers
    user_resolver_file = os.path.join(os.getcwd(), "system/omegaconf/resolvers/resolvers.py")

    if os.path.exists(user_resolver_file):
        try:
            register_user_resolvers(user_resolver_file)
        except Exception as e:
            logger.warning(f"Couldn't import {user_resolver_file}: error {e}")


def register_user_resolvers(user_resolver_file: str) -> None:
    """import user resolvers specified in resolvers_path"""
    if not os.path.exists(user_resolver_file):
        logger.debug(f"File {user_resolver_file} does not exist, ignoring")
        return

    import_path = os.path.dirname(user_resolver_file)

    try:
        sys.path.append(import_path)
        from resolvers import pass_resolvers

        funcs = pass_resolvers()
    except ImportError:
        logger.warning("resolvers.py must contain function 'pass_resolvers()'")
        return
    except Exception as e:
        logger.error(f"resolvers.py: {e}")
        return

    if not isinstance(funcs, dict):
        logger.warning("pass_resolvers() should return a dict")
        return

    import resolvers

    for name, func in funcs.items():
        try:
            OmegaConf.register_new_resolver(name, func, replace=True)
        except:
            logger.warning(f"Could not load resolver {name}")
