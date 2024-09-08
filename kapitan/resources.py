#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"kapitan resources"

import base64
import gzip
import io
import json
import logging
import os
import sys
from functools import partial

import jsonschema
import yaml

import kapitan.cached as cached
from kapitan import __file__ as kapitan_install_path
from kapitan.errors import CompileError, InventoryError, KapitanError
from kapitan.inputs.kadet import Dict
from kapitan.inventory import Inventory, get_inventory_backend
from kapitan.utils import (
    PrettyDumper,
    StrEnum,
    deep_get,
    flatten_dict,
    render_jinja2_file,
    sha256_string,
)

logger = logging.getLogger(__name__)

JSONNET_CACHE = {}

yaml.SafeDumper.add_multi_representer(
    StrEnum,
    yaml.representer.SafeRepresenter.represent_str,
)


def resource_callbacks(search_paths):
    """
    Returns a dict with all the functions to be used
    on the native_callbacks keyword on jsonnet
    search_paths can be used by the native functions to access files
    """

    return {
        "jinja2_render_file": (("name", "ctx"), partial(jinja2_render_file, search_paths)),
        "inventory": (("target", "inv_path"), partial(inventory, search_paths)),
        "file_read": (("name",), partial(read_file, search_paths)),
        "file_exists": (("name",), partial(file_exists, search_paths)),
        "dir_files_list": (("name",), partial(dir_files_list, search_paths)),
        "dir_files_read": (("name",), partial(dir_files_read, search_paths)),
        "sha256_string": (("obj",), sha256_string),
        "gzip_b64": (("obj",), gzip_b64),
        "yaml_dump": (("obj",), yaml_dump),
        "yaml_dump_stream": (("obj",), yaml_dump_stream),
        "yaml_load": (("name",), partial(yaml_load, search_paths)),
        "yaml_load_stream": (("name",), partial(yaml_load_stream, search_paths)),
        "jsonschema_validate": (("obj", "schema_obj"), jsonschema_validate),
    }


def jsonschema_validate(obj, schema_obj):
    """
    validates obj with a schema_obj jsonschema
    returns an object with keys:
    - valid (true/false)
    - reason (will have jsonschema validation error when not valid)
    """
    _obj = json.loads(obj)
    _schema_obj = json.loads(schema_obj)
    try:
        jsonschema.validate(_obj, _schema_obj, format_checker=jsonschema.FormatChecker())
        return {"valid": True, "reason": ""}
    except jsonschema.ValidationError as e:
        return {"valid": False, "reason": "" + str(e)}


def yaml_dump(obj):
    """Dumps jsonnet obj as yaml"""
    _obj = json.loads(obj)
    return yaml.safe_dump(_obj, default_flow_style=False)


def yaml_dump_stream(obj):
    """Dumps jsonnet obj as yaml stream"""
    _obj = json.loads(obj)
    return yaml.safe_dump_all(_obj, default_flow_style=False)


def gzip_b64(obj):
    """returns base64-encoded gzip-compressed obj"""
    obj_bytes = obj.encode("UTF-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as f:
        f.write(obj_bytes)
    compressed_obj = buf.getvalue()
    return base64.b64encode(compressed_obj).decode("UTF-8")


def jinja2_render_file(search_paths, name, ctx):
    """
    Render jinja2 file name with context ctx.
    search_paths is used to find the file name
    as there is a limitation with jsonnet's native_callback approach:
    one can't access the current directory being evaluated
    """
    ctx = json.loads(ctx)
    _full_path = ""

    for path in search_paths:
        _full_path = os.path.join(path, name)
        logger.debug("jinja2_render_file trying file %s", _full_path)
        if os.path.exists(_full_path):
            logger.debug("jinja2_render_file found file at %s", _full_path)
            try:
                return render_jinja2_file(_full_path, ctx, search_paths=search_paths)
            except Exception as e:
                raise CompileError("Jsonnet jinja2 failed to render {}: {}".format(_full_path, e))

    raise IOError("jinja2 failed to render, could not find file: {}".format(_full_path))


def yaml_load(search_paths, name):
    """returns content of yaml file as json string"""
    for path in search_paths:
        _full_path = os.path.join(path, name)
        logger.debug("yaml_load trying file %s", _full_path)
        if os.path.exists(_full_path) and (name.endswith(".yml") or name.endswith(".yaml")):
            logger.debug("yaml_load found file at %s", _full_path)
            try:
                with open(_full_path) as f:
                    return json.dumps(yaml.safe_load(f.read()))
            except Exception as e:
                raise CompileError("Parse yaml failed to parse {}: {}".format(_full_path, e))

    raise IOError("could not find any input yaml file: {}".format(_full_path))


def yaml_load_stream(search_paths, name):
    """returns contents of yaml file as generator"""
    for path in search_paths:
        _full_path = os.path.join(path, name)
        logger.debug("yaml_load_stream trying file %s", _full_path)
        if os.path.exists(_full_path) and (name.endswith(".yml") or name.endswith(".yaml")):
            logger.debug("yaml_load_stream found file at %s", _full_path)
            try:
                with open(_full_path) as f:
                    _obj = yaml.load_all(f.read(), Loader=yaml.SafeLoader)
                    return json.dumps(list(_obj))
            except Exception as e:
                raise CompileError("Parse yaml failed to parse {}: {}".format(_full_path, e))

    raise IOError("could not find any input yaml file: {}".format(_full_path))


def read_file(search_paths, name):
    """return content of file in name"""
    for path in search_paths:
        full_path = os.path.join(path, name)
        logger.debug("read_file trying file %s", full_path)
        if os.path.exists(full_path):
            logger.debug("read_file found file at %s", full_path)
            with io.open(full_path, newline="") as f:
                return f.read()

    raise IOError("Could not find file {}".format(name))


def file_exists(search_paths, name):
    """returns an object with keys:
    - exists (true/false)
    - path (will have the full path where the file was found)"""
    for path in search_paths:
        full_path = os.path.join(path, name)
        logger.debug("file_exists trying file %s", full_path)
        if os.path.exists(full_path):
            logger.debug("file_exists found file at %s", full_path)
            return {"exists": True, "path": full_path}

    return {"exists": False, "path": ""}


def dir_files_list(search_paths, name):
    """returns list of files in a dir"""
    for path in search_paths:
        full_path = os.path.join(path, name)
        logger.debug("dir_files_list trying directory %s", full_path)
        if os.path.exists(full_path):
            return [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
    raise IOError("Could not find folder {}".format(name))


def dir_files_read(search_paths, name):
    """returns an object with key:
    - file_name (contents of the file)"""
    for path in search_paths:
        full_path = os.path.join(path, name)
        logger.debug("dir_files_list trying directory %s", full_path)
        if os.path.exists(full_path):
            return {f: read_file([full_path], f) for f in dir_files_list([full_path], "")}


def search_imports(cwd, import_str, search_paths):
    """
    This is only to be used as a callback for the jsonnet API!
    - cwd is the import context $CWD,
    - import_str is the "bla.jsonnet" in 'import "bla.jsonnet"'
    - search_paths is the location where to look for import_str if not in cwd
    The only supported parameters are cwd and import_str, so search_paths
    needs to be closured.
    This function returns a tuple[str, bytes] since jsonnet 0.19.0 require the
    content of the file to be provided as a bytes type instead of a str.
    """
    basename = os.path.basename(import_str)
    full_import_path = os.path.normpath(os.path.join(cwd, import_str))

    if full_import_path in JSONNET_CACHE:
        return full_import_path, JSONNET_CACHE[full_import_path].encode()

    if not os.path.exists(full_import_path):
        # if import_str not found, search in install_path
        install_path = os.path.dirname(kapitan_install_path)
        _full_import_path = os.path.join(install_path, import_str)
        # if found, set as full_import_path
        if os.path.exists(_full_import_path):
            full_import_path = _full_import_path
            logger.debug("import_str: %s found in search_path: %s", import_str, install_path)
        else:
            # if import_str not found, search in search_paths
            for path in search_paths:
                _full_import_path = os.path.join(path, import_str)
                # if found, set as full_import_path
                if os.path.exists(_full_import_path):
                    full_import_path = _full_import_path
                    logger.debug("import_str: %s found in search_path: %s", import_str, path)
                    break

    # if the above search did not find anything, let jsonnet error
    # with a non existent import
    normalised_path = os.path.normpath(full_import_path)

    logger.debug("cwd:%s import_str:%s basename:%s -> norm:%s", cwd, import_str, basename, normalised_path)

    normalised_path_content = ""
    with open(normalised_path) as f:
        normalised_path_content = f.read()
        JSONNET_CACHE[normalised_path] = normalised_path_content

    return normalised_path, normalised_path_content.encode()


def inventory(search_paths: list = [], target_name: str = None, inventory_path: str = "./inventory"):
    """
    Reads inventory (set by inventory_path) in search_paths.
    set nodes_uri to change reclass nodes_uri the default value
    set target to None to return all target in the inventory
    set inventory_path to read custom path. None defaults to value set via cli
    Returns a dictionary with the inventory for target
    """
    inventory_path = inventory_path or cached.args.inventory_path

    inv_path_exists = False

    # check if the absolute inventory_path exists
    full_inv_path = os.path.abspath(inventory_path)
    if os.path.exists(full_inv_path):
        inv_path_exists = True
    # if not, check for inventory_path in search_paths
    else:
        for path in search_paths:
            full_inv_path = os.path.join(path, inventory_path)
            if os.path.exists(full_inv_path):
                inv_path_exists = True
                break

    if not inv_path_exists:
        raise InventoryError(f"Inventory not found in search paths: {search_paths}")

    logger.debug(f"Using inventory found at {full_inv_path}")
    inv = get_inventory(full_inv_path)

    if target_name:
        target = inv.get_target(target_name)
        return target.model_dump(by_alias=True)

    return inv.inventory


def generate_inventory(args):
    try:
        inv = get_inventory(args.inventory_path)

        if args.target_name:
            inv = inv.inventory[args.target_name]
            if args.pattern:
                pattern = args.pattern.split(".")
                inv = deep_get(inv, pattern)
        else:
            inv = inv.inventory

        if args.flat:
            inv = flatten_dict(inv)
            yaml.dump(inv, sys.stdout, width=10000, default_flow_style=False, indent=args.indent)
        else:
            yaml.dump(inv, sys.stdout, Dumper=PrettyDumper, default_flow_style=False, indent=args.indent)
    except Exception as e:
        if not isinstance(e, KapitanError):
            logger.exception("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        sys.exit(1)


def get_inventory(inventory_path, ignore_class_not_found: bool = False) -> Inventory:
    """
    generic inventory function that makes inventory backend pluggable
    default backend is reclass
    """

    # if inventory is already cached there is nothing to do
    if cached.inv and cached.inv.targets:
        return cached.inv

    compose_target_name = hasattr(cached.args, "compose_target_name") and cached.args.compose_target_name
    if hasattr(cached.args, "compose_node_name") and cached.args.compose_node_name:
        logger.warning(
            "inventory flag '--compose-node-name' is deprecated and scheduled to be dropped with the next release. "
            "Please use '--compose-target-name' instead."
        )
        compose_target_name = True

    # select inventory backend
    backend_id = hasattr(cached.args, "inventory_backend") and cached.args.inventory_backend
    compose_target_name = hasattr(cached.args, "compose_target_name") and cached.args.compose_target_name
    backend = get_inventory_backend(backend_id)

    logger.debug(f"Using {backend.__name__} as inventory backend")
    inventory_backend = backend(
        inventory_path=inventory_path,
        compose_target_name=compose_target_name,
        ignore_class_not_found=ignore_class_not_found,
    )

    cached.inv = inventory_backend
    cached.global_inv = cached.inv.inventory

    # if we use forked processes, we need to load the inventory for kadet once
    # and pass it to the children, to avoid re-reading the inventory for each child
    # TODO(adenaria): Improve to only do it for kadet
    if hasattr(cached.args, "mp_method") and cached.args.mp_method != "spawn":
        cached.inventory_global_kadet = Dict(cached.global_inv)

    # migrate inventory to selected inventory backend
    if hasattr(cached.args, "migrate") and cached.args.migrate:
        inventory_backend.migrate()

    return cached.inv
