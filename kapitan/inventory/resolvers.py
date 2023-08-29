#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import sys

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
    return f"\\${{{content}}}"


def merge(*args):
    """resolver function, that merges omegaconf objects"""
    merge = OmegaConf.merge(*args, list_merge_mode=ListMergeMode.EXTEND)
    return merge


def to_dict(input):
    """resolver function, that converts an object to a dict"""
    if not (isinstance(input, list) or OmegaConf.is_list(input)):
        return input  # not supported

    if not (isinstance(input[0], dict) or OmegaConf.is_dict(input[0])):
        return input

    return {key: item[key] for item in input for key in item}


def to_list(input):
    """resolver function, that converts an object to a list"""
    if isinstance(input, dict) or OmegaConf.is_dict(input):
        return [{item[0]: item[1]} for item in input.items()]

    return list(input)


def default(*args):
    output = ""
    for arg in args[:-1]:
        output += "${oc.select:" + str(arg) + ","

    output += str(args[-1])
    output += "}" * (len(args) - 1)
    return output


def relpath(path: str, _node_):
    """
    resolver function, that translates an absolute yaml-path to its relative path
    """

    node_parts = []
    path_parts = path.split(".")
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
        # print warning for self reference
        return "SELF REFERENCE DETECTED"

    relative_interpolation = "${" + relative_path + "}"

    return relative_interpolation


def write_to_key(location: str, content: dict, _root_):
    """
    resolver function to write any content to different place in the inventory
    NOTE: Behavior for lists is not well defined
    """
    parts = location.split(".")
    key = _root_

    # iterate through parts and create dicts if part not found
    for part in parts:
        if not hasattr(key, part):
            setattr(key, part, {})  # TODO: think about list managing

        # update key
        key = getattr(key, part)

    # update target key
    key.update(content)


def helm_dep(name: str, source: str):
    """kapitan template for a helm chart dependency"""
    return {
        "type": "helm",
        "output_path": f"components/charts/${{{name}.chart_name}}/${{{name}.chart_version}}/${{{name}.application_version}}",
        "source": source,
        "version": f"${{{name}.chart_version}}",
        "chart_name": f"${{{name}.chart_name}}",
    }


def helm_input(name: str):
    """kapitan template for a helm input type configuration"""
    return {
        "input_type": "helm",
        "input_paths": [
            f"components/charts/${{{name}.chart_name}}/${{{name}.chart_version}}/${{{name}.application_version}}"
        ],
        "output_path": f"k8s/${{{name}.namespace}}",
        "helm_params": {
            "namespace": f"${{{name}.namespace}}",
            "name": f"${{{name}.chart_name}}",
            "output_file": f"{name}.yml",
        },
        "helm_values": f"\\${{{name}.helm_values}}",  # \\ used for delaying the resolving of helm values
    }


def register_resolvers(inventory_path: str) -> None:
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
    OmegaConf.register_new_resolver("add", lambda x, y: x + y, replace=replace)
    OmegaConf.register_new_resolver("default", default, replace=replace)
    OmegaConf.register_new_resolver("write", write_to_key, replace=replace)

    # kapitan helpers / templates
    OmegaConf.register_new_resolver("helm_dep", helm_dep, replace=replace)
    OmegaConf.register_new_resolver("helm_input", helm_input, replace=replace)

    # user defined resolvers
    user_resolver_file = os.path.join(inventory_path, "resolvers.py")
    if os.path.exists(user_resolver_file):
        try:
            register_user_resolvers(inventory_path)
        except:
            logger.warning(f"Couldn't import {os.path.join(inventory_path, 'resolvers.py')}")


def register_user_resolvers(inventory_path: str) -> None:
    """import user resolvers specified in inventory/resolvers.py"""
    try:
        import_path = os.path.join(os.getcwd(), inventory_path)
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
