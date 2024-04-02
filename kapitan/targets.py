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
import sys
from collections import defaultdict
from functools import partial

import jsonschema
import yaml
from reclass.errors import NotFoundError, ReclassException

from kapitan import cached, defaults

from kapitan.errors import CompileError, InventoryError, KapitanError


from kapitan.resources import get_inventory
from kapitan.utils import dictionary_hash, directory_hash, hashable_lru_cache
from kapitan.validator.kubernetes_validator import KubernetesManifestValidator

logger = logging.getLogger(__name__)

def generate_inv_cache_hashes(inventory_path, targets, cache_paths):
    """
    generates the hashes for the inventory per target and jsonnet/jinja2 folders for caching purposes
    struct: {
        inventory:
            <target>:
                classes: <sha256>
                parameters: <sha256>
        folder:
            components: <sha256>
            docs: <sha256>
            lib: <sha256>
            scripts: <sha256>
            ...
    }
    """
    inv = get_inventory(inventory_path)
    cached.inv_cache = {}
    cached.inv_cache["inventory"] = {}
    cached.inv_cache["folder"] = {}

    if targets:
        for target in targets:
            try:
                cached.inv_cache["inventory"][target] = {}
                cached.inv_cache["inventory"][target] = dictionary_hash(inv.get_parameters(target))
            except KeyError:
                raise CompileError(f"target not found: {target}")
    else:
        for target in inv.targets.keys():
            cached.inv_cache["inventory"][target] = {}
            cached.inv_cache["inventory"][target] = dictionary_hash(inv.get_parameters(target))

            compile_obj = inv.get_parameters(target)["kapitan"]["compile"]
            for obj in compile_obj:
                for input_path in obj["input_paths"]:
                    base_folder = os.path.dirname(input_path).split("/")[0]
                    if base_folder == "":
                        base_folder = os.path.basename(input_path).split("/")[0]

                    if base_folder not in cached.inv_cache["folder"].keys():
                        if os.path.exists(base_folder) and os.path.isdir(base_folder):
                            cached.inv_cache["folder"][base_folder] = directory_hash(base_folder)

                # Cache additional folders set by --cache-paths
                for path in cache_paths:
                    if path not in cached.inv_cache["folder"].keys():
                        if os.path.exists(path) and os.path.isdir(path):
                            cached.inv_cache["folder"][path] = directory_hash(path)

        # Most commonly changed but not referenced in input_paths
        for common in ("lib", "vendor", "secrets"):
            if common not in cached.inv_cache["folder"].keys():
                if os.path.exists(common) and os.path.isdir(common):
                    cached.inv_cache["folder"][common] = directory_hash(common)


def changed_targets(inventory_path, output_path):
    """returns a list of targets that have changed since last compilation"""
    targets = []
    inv = get_inventory(inventory_path)

    saved_inv_cache = None
    saved_inv_cache_path = os.path.join(output_path, "compiled/.kapitan_cache")
    if os.path.exists(saved_inv_cache_path):
        with open(saved_inv_cache_path, "r") as f:
            try:
                saved_inv_cache = yaml.safe_load(f)
            except Exception:
                raise CompileError("Failed to load kapitan cache: %s", saved_inv_cache_path)

    targets_list = list(inv.targets.keys())

    # If .kapitan_cache doesn't exist or failed to load, recompile all targets
    if not saved_inv_cache:
        return targets_list
    else:
        for key, hash in cached.inv_cache["folder"].items():
            try:
                if hash != saved_inv_cache["folder"][key]:
                    logger.debug("%s folder hash changed, recompiling all targets", key)
                    return targets_list
            except KeyError:
                # Errors usually occur when saved_inv_cache doesn't contain a new folder
                # Recompile anyway to be safe
                return targets_list

        for target in targets_list:
            try:
                if cached.inv_cache["inventory"][target] != saved_inv_cache["inventory"][target]:
                    logger.debug("parameters hash changed in %s, recompiling", target)
                    targets.append(target)
            except KeyError:
                # Errors usually occur when saved_inv_cache doesn't contain a new target
                # Recompile anyway to be safe
                targets.append(target)

    return targets


def save_inv_cache(compile_path, targets):
    """save the cache to .kapitan_cache for inventories per target and folders"""
    if cached.inv_cache:
        inv_cache_path = os.path.join(compile_path, ".kapitan_cache")
        # If only some targets were selected (-t), overwride only their inventory
        if targets:
            saved_inv_cache = None
            try:
                with open(inv_cache_path, "r") as f:
                    saved_inv_cache = yaml.safe_load(f)
            except Exception:
                pass

            if saved_inv_cache:
                if "inventory" not in saved_inv_cache:
                    saved_inv_cache["inventory"] = {}
            else:
                saved_inv_cache = {}
                saved_inv_cache["inventory"] = {}

            for target in targets:
                if target not in saved_inv_cache["inventory"]:
                    saved_inv_cache["inventory"][target] = {}

                saved_inv_cache["inventory"][target] = cached.inv_cache["inventory"][target]

            with open(inv_cache_path, "w") as f:
                logger.debug("Saved .kapitan_cache for targets: %s", targets)
                yaml.dump(saved_inv_cache, stream=f, default_flow_style=False)

        else:
            with open(inv_cache_path, "w") as f:
                logger.debug("Saved .kapitan_cache")
                yaml.dump(cached.inv_cache, stream=f, default_flow_style=False)


def load_target_inventory(inventory_path, targets, ignore_class_notfound=False):
    """returns a list of target objects from the inventory"""
    target_objs = []
    inv = get_inventory(inventory_path)

    # if '-t' is set on compile, only loop through selected targets
    if targets:
        targets_list = targets
    else:
        targets_list = inv.targets.keys()

    for target_name in targets_list:
        try:
            target_obj = inv.get_parameters(target_name, ignore_class_notfound).get("kapitan")
            # check if parameters.kapitan is empty
            if not target_obj:
                raise InventoryError(f"InventoryError: {target_name}: parameters.kapitan has no assignment")
            target_obj["target_full_path"] = inv.targets[target_name].name
            require_compile = not ignore_class_notfound
            valid_target_obj(target_obj, require_compile)
            validate_matching_target_name(target_name, target_obj, inventory_path)
            logger.debug(f"load_target_inventory: found valid kapitan target {target_name}")
            target_objs.append(target_obj)
        except KeyError:
            logger.debug(f"load_target_inventory: target {target_name} has no kapitan compile obj")

    return target_objs


def search_targets(inventory_path, targets, labels):
    """returns a list of targets where the labels match, otherwise just return the original targets"""
    if not labels:
        return targets

    try:
        labels_dict = dict(label.split("=") for label in labels)
    except ValueError:
        raise CompileError(
            "Compile error: Failed to parse labels, should be formatted like: kapitan compile -l env=prod app=example"
        )

    targets_found = []
    inv = get_inventory(inventory_path)

    for target_name in inv.targets.keys():
        matched_all_labels = False
        for label, value in labels_dict.items():
            try:
                if inv.get_parameters(target_name)["kapitan"]["labels"][label] == value:
                    matched_all_labels = True
                    continue
            except KeyError:
                logger.debug(f"search_targets: label {label}={value} didn't match target {target_name}")

            matched_all_labels = False
            break

        if matched_all_labels:
            targets_found.append(target_name)

    if len(targets_found) == 0:
        raise CompileError("No targets found with labels: {labels}")

    return targets_found



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


def schema_validate_compiled(args):
    """
    validates compiled output according to schemas specified in the inventory
    """
    if not os.path.isdir(args.compiled_path):
        logger.error("compiled-path %s not found", args.compiled_path)
        sys.exit(1)

    if not os.path.isdir(args.schemas_path):
        os.makedirs(args.schemas_path)
        logger.info("created schema-cache-path at %s", args.schemas_path)

    worker = partial(schema_validate_kubernetes_output, cache_dir=args.schemas_path)
    pool = multiprocessing.Pool(args.parallelism)

    try:
        target_objs = load_target_inventory(args.inventory_path, args.targets)
        validate_map = create_validate_mapping(target_objs, args.compiled_path)

        [p.get() for p in pool.imap_unordered(worker, validate_map.items()) if p]
        pool.close()

    except ReclassException as e:
        if isinstance(e, NotFoundError):
            logger.error("Inventory reclass error: inventory not found")
        else:
            logger.error("Inventory reclass error: %s", e.message)
        raise InventoryError(e.message)
    except Exception as e:
        pool.terminate()
        logger.debug("Validate pool terminated")
        # only print traceback for errors we don't know about
        if not isinstance(e, KapitanError):
            logger.exception("Unknown (Non-Kapitan) Error occured")

        logger.error("\n")
        logger.error(e)
        sys.exit(1)
    finally:
        # always wait for other worker processes to terminate
        pool.join()


def create_validate_mapping(target_objs, compiled_path):
    """
    creates mapping of (kind, version) tuple to output_paths across different targets
    this is required to avoid redundant schema fetch when multiple targets use the same schema for validation
    """
    validate_files_map = defaultdict(list)
    for target_obj in target_objs:
        target_name = target_obj["vars"]["target"]
        if "validate" not in target_obj:
            logger.debug(
                "target '%s' does not have 'validate' parameter in inventory. skipping",
                target_name,
            )
            continue

        for validate_item in target_obj["validate"]:
            validate_type = validate_item["type"]
            if validate_type == "kubernetes":
                kind_version_pair = (
                    validate_item["kind"],
                    validate_item.get("version", defaults.DEFAULT_KUBERNETES_VERSION),
                )
                for output_path in validate_item["output_paths"]:
                    full_output_path = os.path.join(compiled_path, target_name, output_path)
                    if not os.path.isfile(full_output_path):
                        logger.warning(
                            "%s does not exist for target '%s'. skipping", output_path, target_name
                        )
                        continue
                    validate_files_map[kind_version_pair].append(full_output_path)
            else:
                logger.warning("type %s is not supported for validation. skipping", validate_type)

    return validate_files_map


def schema_validate_kubernetes_output(validate_data, cache_dir):
    """
    validates given files according to kubernetes manifest schemas
    schemas are cached from/to cache_dir
    validate_data must be of structure ((kind, version), validate_files)
    """
    (kind, version), validate_files = validate_data
    KubernetesManifestValidator(cache_dir).validate(validate_files, kind=kind, version=version)
