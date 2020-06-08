#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"kapitan resources"

import base64
import errno
import gzip
import io
import json
import logging
import os
import sys
from functools import partial

import jsonschema
import kapitan.cached as cached
import yaml
from kapitan import __file__ as kapitan_install_path
from kapitan import cached as cached
from kapitan.errors import CompileError, InventoryError, KapitanError
from kapitan.utils import PrettyDumper, deep_get, flatten_dict, render_jinja2_file, sha256_string

import reclass
import reclass.core
from reclass.errors import NotFoundError, ReclassException

logger = logging.getLogger(__name__)

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader


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
    """
    basename = os.path.basename(import_str)
    full_import_path = os.path.join(cwd, import_str)

    if not os.path.exists(full_import_path):
        # if import_str not found, search in install_path
        install_path = os.path.dirname(kapitan_install_path)
        _full_import_path = os.path.join(install_path, import_str)
        # if found, set as full_import_path
        if os.path.exists(_full_import_path):
            full_import_path = _full_import_path
            logger.debug(f"import_str: {import_str} found in search_path: {install_path}")
        else:
            # if import_str not found, search in search_paths
            for path in search_paths:
                _full_import_path = os.path.join(path, import_str)
                # if found, set as full_import_path
                if os.path.exists(_full_import_path):
                    full_import_path = _full_import_path
                    logger.debug(f"import_str: {import_str} found in search_path: {path}")
                    break

    # if the above search did not find anything, let jsonnet error
    # with a non existent import
    normalised_path = os.path.normpath(full_import_path)

    logger.debug("cwd:%s import_str:%s basename:%s -> norm:%s", cwd, import_str, basename, normalised_path)

    normalised_path_content = ""
    with open(normalised_path) as f:
        normalised_path_content = f.read()

    return normalised_path, normalised_path_content


def inventory(search_paths, target, inventory_path="inventory/"):
    """
    Reads inventory (set by inventory_path) in search_paths.
    set nodes_uri to change reclass nodes_uri the default value
    set target to None to return all target in the inventory
    Returns a dictionary with the inventory for target
    """

    full_inv_path = ""
    inv_path_exists = False
    for path in search_paths:
        full_inv_path = os.path.join(path, inventory_path)
        if os.path.exists(full_inv_path):
            inv_path_exists = True
            break

    if not inv_path_exists:
        raise InventoryError(f"Inventory not found in search paths: {search_paths}")

    if target is None:
        return inventory_reclass(full_inv_path)["nodes"]

    return inventory_reclass(full_inv_path)["nodes"][target]


def generate_inventory(args):
    if args.pattern and args.target_name == "":
        parser.error("--pattern requires --target_name")
    try:
        inv = inventory_reclass(args.inventory_path)
        if args.target_name != "":
            inv = inv["nodes"][args.target_name]
            if args.pattern != "":
                pattern = args.pattern.split(".")
                inv = deep_get(inv, pattern)
        if args.flat:
            inv = flatten_dict(inv)
            yaml.dump(inv, sys.stdout, width=10000, default_flow_style=False)
        else:
            yaml.dump(inv, sys.stdout, Dumper=PrettyDumper, default_flow_style=False)
    except Exception as e:
        if not isinstance(e, KapitanError):
            logger.exception("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        sys.exit(1)


def inventory_reclass(inventory_path):
    """
    Runs a reclass inventory in inventory_path
    (same output as running ./reclass.py -b inv_base_uri/ --inventory)
    Will attempt to read reclass config from 'reclass-config.yml' otherwise
    it will failback to the default config.
    Returns a reclass style dictionary
    """

    if not cached.inv:
        reclass_config = {
            "storage_type": "yaml_fs",
            "inventory_base_uri": inventory_path,
            "nodes_uri": os.path.join(inventory_path, "targets"),
            "classes_uri": os.path.join(inventory_path, "classes"),
            "compose_node_name": False,
        }

        try:
            cfg_file = os.path.join(inventory_path, "reclass-config.yml")
            with open(cfg_file) as reclass_cfg:
                reclass_config = yaml.load(reclass_cfg, Loader=YamlLoader)
                # normalise relative nodes_uri and classes_uri paths
                for uri in ("nodes_uri", "classes_uri"):
                    uri_val = reclass_config.get(uri)
                    uri_path = os.path.join(inventory_path, uri_val)
                    normalised_path = os.path.normpath(uri_path)
                    reclass_config.update({uri: normalised_path})
                logger.debug(f"Using reclass inventory config at: {cfg_file}")
        except IOError as ex:
            # If file does not exist, ignore
            if ex.errno == errno.ENOENT:
                logger.debug("Using reclass inventory config defaults")

        try:
            storage = reclass.get_storage(
                reclass_config["storage_type"],
                reclass_config["nodes_uri"],
                reclass_config["classes_uri"],
                reclass_config["compose_node_name"],
            )
            class_mappings = reclass_config.get("class_mappings")  # this defaults to None (disabled)
            _reclass = reclass.core.Core(storage, class_mappings, reclass.settings.Settings(reclass_config))

            cached.inv = _reclass.inventory()
        except ReclassException as e:
            if isinstance(e, NotFoundError):
                logger.error("Inventory reclass error: inventory not found")
            else:
                logger.error("Inventory reclass error: %s", e.message)
            raise InventoryError(e.message)

    return cached.inv
