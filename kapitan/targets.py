#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
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
from kapitan import cached, defaults
from kapitan.dependency_manager.base import fetch_dependencies
from kapitan.errors import CompileError, InventoryError, KapitanError
from kapitan.inputs.copy import Copy
from kapitan.inputs.helm import Helm
from kapitan.inputs.jinja2 import Jinja2
from kapitan.inputs.jsonnet import Jsonnet
from kapitan.inputs.kadet import Kadet
from kapitan.resources import inventory_reclass
from kapitan.utils import dictionary_hash, directory_hash, hashable_lru_cache
from kapitan.validator.kubernetes_validator import KubernetesManifestValidator

from reclass.errors import NotFoundError, ReclassException

logger = logging.getLogger(__name__)


def compile_targets(
    inventory_path, search_paths, output_path, parallel, targets, labels, ref_controller, **kwargs
):
    """
    Searches and loads target files, and runs compile_target() on a
    multiprocessing pool with parallel number of processes.
    kwargs are passed to compile_target()
    """
    # temp_path will hold compiled items
    temp_path = tempfile.mkdtemp(suffix=".kapitan")

    updated_targets = targets
    try:
        updated_targets = search_targets(inventory_path, targets, labels)
    except CompileError as e:
        logger.error(e)
        sys.exit(1)

    # If --cache is set
    if kwargs.get("cache"):
        additional_cache_paths = kwargs.get("cache_paths")
        generate_inv_cache_hashes(inventory_path, targets, additional_cache_paths)

        if not targets:
            updated_targets = changed_targets(inventory_path, output_path)
            logger.debug("Changed targets since last compilation: %s", updated_targets)
            if len(updated_targets) == 0:
                logger.info("No changes since last compilation.")
                return

    pool = multiprocessing.Pool(parallel)

    try:
        target_objs = load_target_inventory(inventory_path, updated_targets)

        # append "compiled" to output_path so we can safely overwrite it
        compile_path = os.path.join(output_path, "compiled")
        worker = partial(
            compile_target,
            search_paths=search_paths,
            compile_path=temp_path,
            ref_controller=ref_controller,
            **kwargs,
        )

        if not target_objs:
            raise CompileError("Error: no targets found")

        if kwargs.get("fetch_dependencies", False):
            fetch_dependencies(target_objs, pool)

        # compile_target() returns None on success
        # so p is only not None when raising an exception
        [p.get() for p in pool.imap_unordered(worker, target_objs) if p]

        os.makedirs(compile_path, exist_ok=True)

        # if '-t' is set on compile or only a few changed, only override selected targets
        if updated_targets:
            for target in updated_targets:
                compile_path_target = os.path.join(compile_path, target)
                temp_path_target = os.path.join(temp_path, target)

                os.makedirs(compile_path_target, exist_ok=True)

                shutil.rmtree(compile_path_target)
                shutil.copytree(temp_path_target, compile_path_target)
                logger.debug("Copied %s into %s", temp_path_target, compile_path_target)
        # otherwise override all targets
        else:
            shutil.rmtree(compile_path)
            shutil.copytree(temp_path, compile_path)
            logger.debug("Copied %s into %s", temp_path, compile_path)

        # validate the compiled outputs
        if kwargs.get("validate", False):
            validate_map = create_validate_mapping(target_objs, compile_path)
            worker = partial(
                schema_validate_kubernetes_output, cache_dir=kwargs.get("schemas_path", "./schemas")
            )
            [p.get() for p in pool.imap_unordered(worker, validate_map.items()) if p]

        # Save inventory and folders cache
        save_inv_cache(compile_path, targets)
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
            logger.exception("Unknown (Non-Kapitan) Error occurred")

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
    inv = inventory_reclass(inventory_path)
    cached.inv_cache = {}
    cached.inv_cache["inventory"] = {}
    cached.inv_cache["folder"] = {}

    if targets:
        for target in targets:
            try:
                cached.inv_cache["inventory"][target] = {}
                cached.inv_cache["inventory"][target]["classes"] = dictionary_hash(
                    inv["nodes"][target]["classes"]
                )
                cached.inv_cache["inventory"][target]["parameters"] = dictionary_hash(
                    inv["nodes"][target]["parameters"]
                )
            except KeyError:
                raise CompileError("target not found: {}".format(target))
    else:
        for target in inv["nodes"]:
            cached.inv_cache["inventory"][target] = {}
            cached.inv_cache["inventory"][target]["classes"] = dictionary_hash(
                inv["nodes"][target]["classes"]
            )
            cached.inv_cache["inventory"][target]["parameters"] = dictionary_hash(
                inv["nodes"][target]["parameters"]
            )

            compile_obj = inv["nodes"][target]["parameters"]["kapitan"]["compile"]
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
    inv = inventory_reclass(inventory_path)

    saved_inv_cache = None
    saved_inv_cache_path = os.path.join(output_path, "compiled/.kapitan_cache")
    if os.path.exists(saved_inv_cache_path):
        with open(saved_inv_cache_path, "r") as f:
            try:
                saved_inv_cache = yaml.safe_load(f)
            except Exception:
                raise CompileError("Failed to load kapitan cache: %s", saved_inv_cache_path)

    targets_list = list(inv["nodes"])

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
                if (
                    cached.inv_cache["inventory"][target]["classes"]
                    != saved_inv_cache["inventory"][target]["classes"]
                ):
                    logger.debug("classes hash changed in %s, recompiling", target)
                    targets.append(target)
                elif (
                    cached.inv_cache["inventory"][target]["parameters"]
                    != saved_inv_cache["inventory"][target]["parameters"]
                ):
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

                saved_inv_cache["inventory"][target]["classes"] = cached.inv_cache["inventory"][target][
                    "classes"
                ]
                saved_inv_cache["inventory"][target]["parameters"] = cached.inv_cache["inventory"][target][
                    "parameters"
                ]

            with open(inv_cache_path, "w") as f:
                logger.debug("Saved .kapitan_cache for targets: %s", targets)
                yaml.dump(saved_inv_cache, stream=f, default_flow_style=False)

        else:
            with open(inv_cache_path, "w") as f:
                logger.debug("Saved .kapitan_cache")
                yaml.dump(cached.inv_cache, stream=f, default_flow_style=False)


def load_target_inventory(inventory_path, targets):
    """returns a list of target objects from the inventory"""
    target_objs = []
    inv = inventory_reclass(inventory_path)

    # if '-t' is set on compile, only loop through selected targets
    if targets:
        targets_list = targets
    else:
        targets_list = inv["nodes"]

    for target_name in targets_list:
        try:
            inv_target = inv["nodes"][target_name]
            target_obj = inv_target["parameters"]["kapitan"]
            target_obj["target_full_path"] = inv_target["__reclass__"]["node"].replace("./", "")
            valid_target_obj(target_obj)
            validate_matching_target_name(target_name, target_obj, inventory_path)
            logger.debug("load_target_inventory: found valid kapitan target %s", target_name)
            target_objs.append(target_obj)
        except KeyError:
            logger.debug("load_target_inventory: target %s has no kapitan compile obj", target_name)
            pass

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
    inv = inventory_reclass(inventory_path)

    for target_name in inv["nodes"]:
        matched_all_labels = False
        for label, value in labels_dict.items():
            try:
                if inv["nodes"][target_name]["parameters"]["kapitan"]["labels"][label] == value:
                    matched_all_labels = True
                    continue
            except KeyError:
                logger.debug("search_targets: label %s=%s didn't match target %s", label, value, target_name)

            matched_all_labels = False
            break

        if matched_all_labels:
            targets_found.append(target_name)

    if len(targets_found) == 0:
        raise CompileError("No targets found with labels: {}".format(labels))

    return targets_found


def compile_target(target_obj, search_paths, compile_path, ref_controller, **kwargs):
    """Compiles target_obj and writes to compile_path"""
    start = time.time()
    compile_objs = target_obj["compile"]
    ext_vars = target_obj["vars"]
    target_name = ext_vars["target"]

    jinja2_compiler = Jinja2(compile_path, search_paths, ref_controller)
    jsonnet_compiler = Jsonnet(compile_path, search_paths, ref_controller)
    kadet_compiler = Kadet(compile_path, search_paths, ref_controller)
    helm_compiler = Helm(compile_path, search_paths, ref_controller)
    copy_compiler = Copy(compile_path, search_paths, ref_controller)

    for comp_obj in compile_objs:
        input_type = comp_obj["input_type"]
        output_path = comp_obj["output_path"]
        if input_type == "jinja2":
            input_compiler = jinja2_compiler
        elif input_type == "jsonnet":
            input_compiler = jsonnet_compiler
        elif input_type == "kadet":
            input_compiler = kadet_compiler
        elif input_type == "helm":
            if "helm_values" in comp_obj:
                helm_compiler.dump_helm_values(comp_obj["helm_values"])
            if "helm_params" in comp_obj:
                helm_compiler.set_helm_params(comp_obj["helm_params"])
            input_compiler = helm_compiler
        elif input_type == "copy":
            input_compiler = copy_compiler
        else:
            err_msg = 'Invalid input_type: "{}". Supported input_types: jsonnet, jinja2, kadet, helm, copy'
            raise CompileError(err_msg.format(input_type))

        input_compiler.make_compile_dirs(target_name, output_path)
        input_compiler.compile_obj(comp_obj, ext_vars, **kwargs)

    logger.info("Compiled %s (%.2fs)", target_obj["target_full_path"], time.time() - start)


@hashable_lru_cache
def valid_target_obj(target_obj):
    """
    Validates a target_obj
    Returns a dict object if target is valid
    Otherwise raises ValidationError
    """

    schema = {
        "type": "object",
        "properties": {
            "vars": {"type": "object"},
            "secrets": {"type": "object"},
            "compile": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "input_paths": {"type": "array"},
                        "input_type": {"type": "string"},
                        "output_path": {"type": "string"},
                        "output_type": {"type": "string"},
                        "helm_values": {"type": "object"},
                        "helm_params": {
                            "type": "object",
                            "properties": {
                                "namespace": {"type": "string"},
                                "name_template": {"type": "string"},
                                "release_name": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    },
                    "required": ["input_type", "input_paths", "output_path"],
                    "minItems": 1,
                    "oneOf": [
                        {
                            "properties": {
                                "input_type": {"enum": ["jsonnet", "kadet", "copy"]},
                                "output_type": {"enum": ["yaml", "json", "plain"]},
                            },
                        },
                        {"properties": {"input_type": {"enum": ["jinja2", "helm"]}}},
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
                                "properties": {"type": {}, "kind": {}, "output_paths": {}, "version": {}},
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
                                },
                                "required": ["type", "output_path", "source", "chart_name"],
                                "additionalProperties": False,
                            },
                        },
                    ],
                },
            },
        },
        "required": ["compile"],
    }

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
    logger.debug(f"validating target name matches the name of yml file {target_filename}")
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
        logger.error(f"compiled-path {args.compiled_path} not found")
        sys.exit(1)

    if not os.path.isdir(args.schemas_path):
        os.makedirs(args.schemas_path)
        logger.info(f"created schema-cache-path at {args.schemas_path}")

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
                "target '{}' does not have 'validate' parameter in inventory. skipping".format(target_name)
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
                        logger.warning(f"{output_path} does not exist for target '{target_name}'. skipping")
                        continue
                    validate_files_map[kind_version_pair].append(full_output_path)
            else:
                logger.warning(f"type {validate_type} is not supported for validation. skipping")

    return validate_files_map


def schema_validate_kubernetes_output(validate_data, cache_dir):
    """
    validates given files according to kubernetes manifest schemas
    schemas are cached from/to cache_dir
    validate_data must be of structure ((kind, version), validate_files)
    """
    (kind, version), validate_files = validate_data
    KubernetesManifestValidator(cache_dir).validate(validate_files, kind=kind, version=version)
