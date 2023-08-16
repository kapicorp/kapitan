#!/usr/bin/env python3

# Copyright 2023 nexenio

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


def relpath(path: str, _node_: Node):
    """resolver function, that translates an absolute yaml-path to its relativ path"""
    start = _node_._get_full_key("")
    start = start.replace("[", ".")

    path_parts = path.split(".")
    start_parts = start.split(".")

    while path_parts and start_parts and path_parts[0] == start_parts[0]:
        path_parts.pop(0)
        start_parts.pop(0)

    # Construct relative path
    rel_parts = ["."] * (len(start_parts))
    reminder_path = ".".join(path_parts)

    rel_path = "".join(rel_parts) + reminder_path

    return f"${{{rel_path}}}"


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

    # yaml key utility functions
    OmegaConf.register_new_resolver("key", key)
    OmegaConf.register_new_resolver("parentkey", parentkey)
    OmegaConf.register_new_resolver("fullkey", fullkey)
    OmegaConf.register_new_resolver("relpath", relpath)

    # yaml object utility functions
    OmegaConf.register_new_resolver("access", access_key_with_dots)
    OmegaConf.register_new_resolver("merge", merge)
    OmegaConf.register_new_resolver("dict", to_dict)
    OmegaConf.register_new_resolver("list", to_list)

    # kapitan helpers / templates
    OmegaConf.register_new_resolver("helm_dep", helm_dep)
    OmegaConf.register_new_resolver("helm_input", helm_input)

    # user defined resolvers
    user_resolver_file = os.path.join(inventory_path, "resolvers.py")
    if os.path.exists(user_resolver_file):
        try:
            register_user_resolvers(inventory_path)
        except:
            logger.debug(f"Couldn't import {os.join(inventory_path, 'resolvers.py')}")


def register_user_resolvers(inventory_path: str) -> None:
    """import user resolvers specified in inventory/resolvers.py"""
    try:
        import_path = os.path.join(os.getcwd(), inventory_path)
        sys.path.append(import_path)
        from resolvers import pass_resolvers

        funcs = pass_resolvers()
    except:
        logger.warning("resolvers.py must contain function 'pass_resolvers()'")
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
