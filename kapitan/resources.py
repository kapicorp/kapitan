#!/usr/bin/env python3.6
#
# Copyright 2018 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"kapitan resources"

import errno
from functools import partial
import ujson as json
import logging
import os
import io
import reclass
import reclass.core
from reclass.errors import ReclassException, NotFoundError
import yaml

from kapitan.utils import render_jinja2_file, sha256_string
from kapitan import __file__ as kapitan_install_path
from kapitan.errors import CompileError, InventoryError
import kapitan.cached as cached

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

    return {"jinja2_render_file": (("name", "ctx"),
                                   partial(jinja2_render_file, search_paths)),
            "inventory": (("target", "inv_path"),
                          partial(inventory, search_paths)),
            "file_read": (("name",),
                          partial(read_file, search_paths)),
            "yaml_dump": (("obj",), yaml_dump),
            "sha256_string": (("obj",), sha256_string),
           }


def yaml_dump(obj):
    """Dumps jsonnet obj as yaml"""
    _obj = json.loads(obj)
    return yaml.safe_dump(_obj, default_flow_style=False)


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
                return render_jinja2_file(_full_path, ctx)
            except Exception as e:
                logger.error("Jsonnet jinja2 failed to render %s: %s", _full_path, str(e))
                raise CompileError(e)

    raise IOError("jinja2 failed to render, could not find file: {}".format(_full_path))


def read_file(search_paths, name):
    """return content of file in name"""
    for path in search_paths:
        full_path = os.path.join(path, name)
        logger.debug("read_file trying file %s", full_path)
        if os.path.exists(full_path):
            logger.debug("read_file found file at %s", full_path)
            with io.open(full_path, newline='') as f:
                return f.read()

    raise IOError("Could not find file {}".format(name))


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
            logger.debug("import_str: %s found in search_path: %s",
                         import_str, install_path)
        else:
            # if import_str not found, search in search_paths
            for path in search_paths:
                _full_import_path = os.path.join(path, import_str)
                # if found, set as full_import_path
                if os.path.exists(_full_import_path):
                    full_import_path = _full_import_path
                    logger.debug("import_str: %s found in search_path: %s",
                                 import_str, path)
                    break

    # if the above search did not find anything, let jsonnet error
    # with a non existent import
    normalised_path = os.path.normpath(full_import_path)

    logger.debug("cwd:%s import_str:%s basename:%s -> norm:%s",
                 cwd, import_str, basename, normalised_path)

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
        logger.error("Inventory not found in search paths: %s", search_paths)
        raise InventoryError()

    if target is None:
        return inventory_reclass(full_inv_path)["nodes"]

    return inventory_reclass(full_inv_path)["nodes"][target]


def inventory_reclass(inventory_path):
    """
    Runs a reclass inventory in inventory_path
    (same output as running ./reclass.py -b streams/ --inventory)
    Will attempt to read reclass config from 'reclass-config.yml' otherwise
    it will failback to the default config.
    Returns a reclass style dictionary
    """

    if not cached.inv:
        reclass_config = {'storage_type': 'yaml_fs',
                          'inventory_base_uri': inventory_path,
                          'nodes_uri': os.path.join(inventory_path, 'targets'),
                          'classes_uri': os.path.join(inventory_path, 'classes')
                         }

        try:
            cfg_file = os.path.join(inventory_path, 'reclass-config.yml')
            with open(cfg_file) as reclass_cfg:
                reclass_config = yaml.load(reclass_cfg, Loader=YamlLoader)
                # normalise relative nodes_uri and classes_uri paths
                for uri in ('nodes_uri', 'classes_uri'):
                    uri_val = reclass_config.get(uri)
                    uri_path = os.path.join(inventory_path, uri_val)
                    normalised_path = os.path.normpath(uri_path)
                    reclass_config.update({uri: normalised_path})
                logger.debug("Using reclass inventory config at: %s", cfg_file)
        except IOError as ex:
            # If file does not exist, ignore
            if ex.errno == errno.ENOENT:
                logger.debug("Using reclass inventory config defaults")

        try:
            storage = reclass.get_storage(reclass_config['storage_type'], reclass_config['nodes_uri'],
                                          reclass_config['classes_uri'])
            class_mappings = reclass_config.get('class_mappings')  # this defaults to None (disabled)
            _reclass = reclass.core.Core(storage, class_mappings, reclass.settings.Settings())

            cached.inv = _reclass.inventory()
        except ReclassException as e:
            if isinstance(e, NotFoundError):
                logger.error("Inventory reclass error: inventory not found")
            else:
                logger.error("Inventory reclass error: %s", e.message)
            raise InventoryError(e.message)

    return cached.inv
