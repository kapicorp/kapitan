#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"kapitan targets"
import json
import logging
import multiprocessing
import os
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from functools import partial

import jsonschema
import yaml
from reclass.errors import NotFoundError, ReclassException

from kapitan import cached, defaults
from kapitan.dependency_manager.base import fetch_dependencies
from kapitan.remoteinventory.fetch import fetch_inventories, list_sources
from kapitan.errors import CompileError, InventoryError, KapitanError
from kapitan.inputs.copy import Copy
from kapitan.inputs.external import External
from kapitan.inputs.helm import Helm
from kapitan.inputs.jinja2 import Jinja2
from kapitan.inputs.jsonnet import Jsonnet
from kapitan.inputs.kadet import Kadet
from kapitan.inputs.remove import Remove
from kapitan.inventory import Inventory, ReclassInventory
from kapitan.utils import hashable_lru_cache
from kapitan.validator.kubernetes_validator import KubernetesManifestValidator

logger = logging.getLogger(__name__)


def compile_targets(
    inventory_path, search_paths, output_path, parallel, targets, labels, ref_controller, **kwargs
):
    _ = ReclassInventory(inventory_path)
    """
    Searches and loads target files, and runs compile_target() on a
    multiprocessing pool with parallel number of processes.
    kwargs are passed to compile_target()
    """
    # temp_path will hold compiled items
    temp_path = tempfile.mkdtemp(suffix=".kapitan")
    # enable previously compiled items to be reference in other compile inputs
    search_paths.append(temp_path)
    temp_compile_path = os.path.join(temp_path, "compiled")
    dep_cache_dir = temp_path

    pool = multiprocessing.Pool(parallel)

    updated_targets = Inventory.get().search_targets()

    try:
        rendering_start = time.time()

        # check if --fetch or --force-fetch is enabled
        force_fetch = kwargs.get("force_fetch", False)
        fetch = kwargs.get("fetch", False) or force_fetch

        # deprecated --force flag
        if kwargs.get("force", False):
            logger.info(
                "DeprecationWarning: --force is deprecated. Use --force-fetch instead of --force --fetch"
            )
            force_fetch = True

        if fetch:
            # skip classes that are not yet available
            target_objs = load_target_inventory(updated_targets)
        else:
            # ignore_class_notfound = False by default
            target_objs = load_target_inventory(updated_targets)

        # append "compiled" to output_path so we can safely overwrite it
        compile_path = os.path.join(output_path, "compiled")

        if not target_objs:
            raise CompileError("Error: no targets found")

        logger.info("Rendered inventory (%.2fs)", time.time() - rendering_start)

        worker = partial(
            compile_target,
            search_paths=search_paths,
            compile_path=temp_compile_path,
            ref_controller=ref_controller,
            inventory_path=inventory_path,
            globals_cached=cached.as_dict(),
            **kwargs,
        )

        # compile_target() returns None on success
        # so p is only not None when raising an exception
        [p.get() for p in pool.imap_unordered(worker, target_objs.values()) if p]

        os.makedirs(compile_path, exist_ok=True)

        # if '-t' is set on compile or only a few changed, only override selected targets
        if updated_targets:
            for target in target_objs.values():
                path = target["_reclass_"]["name"]["path"]
                compile_path_target = os.path.join(compile_path, path)
                temp_path_target = os.path.join(temp_compile_path, path)

                os.makedirs(compile_path_target, exist_ok=True)

                shutil.rmtree(compile_path_target)
                shutil.copytree(temp_path_target, compile_path_target)
                logger.debug("Copied %s into %s", temp_path_target, compile_path_target)
        # otherwise override all targets
        else:
            shutil.rmtree(compile_path)
            shutil.copytree(temp_compile_path, compile_path)
            logger.debug("Copied %s into %s", temp_compile_path, compile_path)

        pool.close()

    except ReclassException as e:
        if isinstance(e, NotFoundError):
            logger.error("Inventory reclass error: inventory not found")
        else:
            logger.error("Inventory reclass error: %s", e.message)
        raise InventoryError(e.message)
    except Exception as e:
        # if compile worker fails, terminate immediately
        pool.terminate()
        logger.debug("Compile pool terminated")
        # only print traceback for errors we don't know about
        if not isinstance(e, KapitanError):
            logger.exception("\nUnknown (Non-Kapitan) error occurred:\n")

        logger.error("\n")
        if kwargs.get("verbose"):
            logger.exception(e)
        else:
            logger.error(e)
        sys.exit(1)
    finally:
        # always wait for other worker processes to terminate
        pool.join()
        shutil.rmtree(temp_path)
        logger.debug("Removed %s", temp_path)


def load_target_inventory(targets):
    """returns a list of target objects from the inventory"""

    # if '-t' is set on compile, only loop through selected targets
    if not targets:
        return Inventory.get().inventory
    else:
        return Inventory.get().get_targets(targets)


# def filter_targets_to_compile(targets, labels):
#     """returns a list of targets where the labels match, otherwise just return the original targets"""
#     if not labels:
#         return targets

#     try:
#         labels_dict = dict(label.split("=") for label in labels)
#     except ValueError:
#         raise CompileError(
#             "Failed to parse labels. Your command should be formatted like: kapitan compile --labels env=prod app=example"
#         )

#     for target_name in targets:
#         matched_all_labels = False
#         for label, value in labels_dict.items():
#             try:
#                 if inv["nodes"][target_name]["parameters"]["kapitan"]["labels"][label] == value:
#                     matched_all_labels = True
#                     continue
#             except KeyError:
#                 logger.debug("search_targets: label %s=%s didn't match target %s", label, value, target_name)

#             matched_all_labels = False
#             break

#         if matched_all_labels:
#             targets_found.append(target_name)

#     return targets_found


def compile_target(target_obj, search_paths, compile_path, ref_controller, globals_cached=None, **kwargs):
    """Compiles target_obj and writes to compile_path"""
    start = time.time()
    target_obj = target_obj["kapitan"]
    compile_objs = target_obj["compile"]
    ext_vars = target_obj["vars"]
    target_name = ext_vars["target"]

    if globals_cached:
        cached.from_dict(globals_cached)

    use_go_jsonnet = kwargs.get("use_go_jsonnet", False)
    if use_go_jsonnet:
        logger.debug("Using go-jsonnet over jsonnet")

    for comp_obj in compile_objs:
        input_type = comp_obj["input_type"]
        output_path = comp_obj["output_path"]
        input_params = comp_obj.setdefault("input_params", {})

        if input_type == "jinja2":
            input_compiler = Jinja2(compile_path, search_paths, ref_controller, comp_obj)
        elif input_type == "jsonnet":
            input_compiler = Jsonnet(compile_path, search_paths, ref_controller, use_go=use_go_jsonnet)
        elif input_type == "kadet":
            input_compiler = Kadet(compile_path, search_paths, ref_controller, input_params=input_params)
        elif input_type == "helm":
            input_compiler = Helm(compile_path, search_paths, ref_controller, comp_obj)
        elif input_type == "copy":
            ignore_missing = comp_obj.get("ignore_missing", False)
            input_compiler = Copy(compile_path, search_paths, ref_controller, ignore_missing)
        elif input_type == "remove":
            input_compiler = Remove(compile_path, search_paths, ref_controller)
        elif input_type == "external":
            input_compiler = External(compile_path, search_paths, ref_controller)
            if "args" in comp_obj:
                input_compiler.set_args(comp_obj["args"])
            if "env_vars" in comp_obj:
                input_compiler.set_env_vars(comp_obj["env_vars"])
        else:
            err_msg = 'Invalid input_type: "{}". Supported input_types: jsonnet, jinja2, kadet, helm, copy, remove, external'
            raise CompileError(err_msg.format(input_type))

        input_compiler.make_compile_dirs(target_name, output_path, **kwargs)
        input_compiler.compile_obj(comp_obj, ext_vars, **kwargs)

    logger.info(f"Compiled target ({time.time() - start:.2f}s)")


@hashable_lru_cache
def valid_target_obj(target_obj, require_compile=True):
    """
    Validates a target_obj
    Returns a dict object if target is valid
    Otherwise raises ValidationError
    """

    schema = {
        "type": "object",
        "properties": {
            "vars": {"type": "object"},
            "secrets": {
                "type": "object",
                "properties": {
                    "gpg": {
                        "type": "object",
                        "properties": {
                            "recipients": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "fingerprint": {"type": "string"},
                                    },
                                },
                            },
                        },
                        "required": ["recipients"],
                    },
                    "gkms": {
                        "type": "object",
                        "properties": {"key": {"type": "string"}},
                        "required": ["key"],
                    },
                    "awskms": {
                        "type": "object",
                        "properties": {"key": {"type": "string"}},
                        "required": ["key"],
                    },
                    "azkms": {
                        "type": "object",
                        "properties": {"key": {"type": "string"}},
                        "required": ["key"],
                    },
                    "vaultkv": {
                        "type": "object",
                        "properties": {
                            "VAULT_ADDR": {"type": "string"},
                            "VAULT_NAMESPACE": {"type": "string"},
                            "VAULT_SKIP_VERIFY": {"type": "string"},
                            "VAULT_CLIENT_KEY": {"type": "string"},
                            "VAULT_CLIENT_CERT": {"type": "string"},
                            "auth": {"enum": ["token", "userpass", "ldap", "github", "approle"]},
                            "engine": {"type": "string"},
                            "mount": {"type": "string"},
                        },
                    },
                    "vaulttransit": {
                        "type": "object",
                        "properties": {
                            "VAULT_ADDR": {"type": "string"},
                            "VAULT_NAMESPACE": {"type": "string"},
                            "VAULT_SKIP_VERIFY": {"type": "string"},
                            "VAULT_CLIENT_KEY": {"type": "string"},
                            "VAULT_CLIENT_CERT": {"type": "string"},
                            "auth": {"enum": ["token", "userpass", "ldap", "github", "approle"]},
                            "engine": {"type": "string"},
                            "mount": {"type": "string"},
                            "key": {"type": "string"},
                        },
                    },
                },
                "additionalProperties": False,
            },
            "compile": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "input_paths": {"type": "array"},
                        "input_type": {"type": "string"},
                        "output_path": {"type": "string"},
                        "output_type": {"type": "string"},
                        "helm_values": {"type": "object"},
                        "helm_values_files": {"type": "array"},
                        "helm_params": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "additionalProperties": True,
                        },
                        "input_params": {"type": "object"},
                        "env_vars": {"type": "object"},
                        "args": {"type": "array"},
                        "suffix_remove": {"type": "boolean"},
                        "suffix_stripped": {"type": "string"},
                    },
                    "required": ["input_type", "input_paths", "output_path"],
                    "minItems": 1,
                    "oneOf": [
                        {
                            "properties": {
                                "input_type": {"enum": ["jsonnet", "kadet", "copy", "remove"]},
                                "output_type": {"enum": ["yml", "yaml", "json", "plain", "toml"]},
                            },
                        },
                        {"properties": {"input_type": {"enum": ["jinja2", "helm", "external"]}}},
                    ],
                },
            },
            "validate": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "output_paths": {"type": "array"},
                        "type": {"type": "string", "enum": ["kubernetes"]},
                        "kind": {"type": "string"},
                        "version": {"type": "string"},
                    },
                    "required": ["output_paths", "type"],
                    "minItems": 1,
                    "allOf": [
                        {
                            "if": {"properties": {"type": {"const": "kubernetes"}}},
                            "then": {
                                "properties": {
                                    "type": {},
                                    "kind": {},
                                    "output_paths": {},
                                    "version": {},
                                },
                                "additionalProperties": False,
                                "required": ["kind"],
                            },
                        },
                    ],
                },
            },
            "dependencies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chart_name": {"type": "string"},
                        "type": {"type": "string", "enum": ["git", "http", "https", "helm"]},
                        "output_path": {"type": "string"},
                        "source": {"type": "string"},
                        "subdir": {"type": "string"},
                        "ref": {"type": "string"},
                        "unpack": {"type": "boolean"},
                        "version": {"type": "string"},
                        "force_fetch": {"type": "boolean"},
                        "submodules": {"type": "boolean"},
                    },
                    "required": ["type", "output_path", "source"],
                    "additionalProperties": False,
                    "allOf": [
                        {
                            "if": {"properties": {"type": {"enum": ["http", "https"]}}},
                            "then": {
                                "properties": {
                                    "type": {},
                                    "source": {"format": "uri"},
                                    "output_path": {},
                                    "unpack": {},
                                    "force_fetch": {},
                                },
                                "additionalProperties": False,
                            },
                        },
                        {
                            "if": {"properties": {"type": {"enum": ["helm"]}}},
                            "then": {
                                "properties": {
                                    "type": {},
                                    "source": {"format": "uri"},
                                    "output_path": {},
                                    "unpack": {},
                                    "chart_name": {"type": "string"},
                                    "version": {"type": "string"},
                                    "force_fetch": {},
                                },
                                "required": ["type", "output_path", "source", "chart_name"],
                                "additionalProperties": False,
                            },
                        },
                    ],
                },
            },
            "inventory": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["git", "http", "https"]},
                        "output_path": {"type": "string"},
                        "source": {"type": "string"},
                        "subdir": {"type": "string"},
                        "ref": {"type": "string"},
                        "unpack": {"type": "boolean"},
                    },
                    "required": ["type", "output_path", "source"],
                    "additionalProperties": False,
                    "allOf": [
                        {
                            "if": {"properties": {"type": {"enum": ["http", "https"]}}},
                            "then": {
                                "properties": {
                                    "type": {},
                                    "source": {"format": "uri"},
                                    "output_path": {},
                                    "unpack": {},
                                },
                                "additionalProperties": False,
                            },
                        },
                    ],
                },
            },
        },
    }
    if require_compile:
        schema["required"] = ["compile"]

    try:
        jsonschema.validate(target_obj, schema, format_checker=jsonschema.FormatChecker())
    except jsonschema.exceptions.ValidationError as e:
        raise InventoryError(
            "Invalid inventory structure\n\nError: {}\nOn instance:\n{}".format(
                e.message, json.dumps(e.instance, indent=2, sort_keys=False)
            )
        )


def validate_matching_target_name(target_filename, target_obj, inventory_path):
    """Throws *InventoryError* if parameters.kapitan.vars.target is not set,
    or target does not have a corresponding yaml file in *inventory_path*
    """
    logger.debug("validating target name matches the name of yml file %s", target_filename)
    try:
        target_name = target_obj["vars"]["target"]
    except KeyError:
        error_message = (
            f'Target missing: target "{target_filename}" is missing parameters.kapitan.vars.target\n'
            "This parameter should be set to the target name"
        )
        raise InventoryError(error_message)

    if target_filename != target_name:
        target_path = os.path.join(os.path.abspath(inventory_path), "targets")

        error_message = (
            f'Target "{target_name}" is missing the corresponding yml file in {target_path}\n'
            "Target name should match the name of the target yml file in inventory"
        )
        raise InventoryError(error_message)
