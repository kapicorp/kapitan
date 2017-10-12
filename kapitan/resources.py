#!/usr/bin/python
#
# Copyright 2017 The Kapitan Authors
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
import json
import logging
import os
import reclass
import reclass.core
import yaml

from kapitan.utils import render_jinja2_file, memoize

logger = logging.getLogger(__name__)


def resource_callbacks(search_path):
    """
    Returns a dict with all the functions to be used
    on the native_callbacks keyword on jsonnet
    search_path can be used by the native functions to access files
    """

    return {"jinja2_render_file": (("name", "ctx"),
                                   partial(jinja2_render_file, search_path)),
            "inventory": (("target", "inv_path"),
                          partial(inventory, search_path)),
            "file_read": (("name",),
                          partial(read_file, search_path)),
           }


def jinja2_render_file(search_path, name, ctx):
    """
    Render jinja2 file name with context ctx.
    search_path is used to find the file name
    as there is a limitation with jsonnet's native_callback approach:
    one can't access the current directory being evaluated
    """
    ctx = json.loads(ctx)
    _full_path = os.path.join(search_path, name)
    logger.debug("jinja2_render_file trying file %s", _full_path)
    if os.path.exists(_full_path):
        logger.debug("jinja2_render_file found file at %s", _full_path)
        return render_jinja2_file(_full_path, ctx)
    # default IOError if we reach here
    raise IOError("Could not find file %s" % name)


def read_file(search_path, name):
    "return content of file in name"
    full_path = os.path.join(search_path, name)
    logger.debug("read_file trying file %s", full_path)
    if os.path.exists(full_path):
        logger.debug("read_file found file at %s", full_path)
        with open(full_path) as f:
            return f.read()
    raise IOError("Could not find file %s" % name)


def search_imports(cwd, import_str, search_path):
    """
    This is only to be used as a callback for the jsonnet API!
    - cwd is the import context $CWD,
    - import_str is the "bla.jsonnet" in 'import "bla.jsonnet"'
    - search_path is the location where to look for import_str if not in cwd
    The only supported parameters are cwd and import_str, so search_path
    needs to be closured.
    """
    basename = os.path.basename(import_str)
    full_import_path = os.path.join(cwd, import_str)

    # if import_str not found, search in search_path
    if not os.path.exists(full_import_path):
        _full_import_path = os.path.join(search_path, import_str)
        # if found, set as full_import_path
        if os.path.exists(_full_import_path):
            full_import_path = _full_import_path
            logger.debug("import_str: %s found in search_path: %s",
                         import_str, search_path)

    normalised_path = os.path.normpath(full_import_path)

    logger.debug("cwd:%s import_str:%s basename:%s -> norm:%s",
                 cwd, import_str, basename, normalised_path)

    return normalised_path, open(normalised_path).read()


def inventory(search_path, target, inventory_path="inventory/"):
    """
    Reads inventory (set by inventory_path) in search_path.
    set nodes_uri to change reclass nodes_uri the default value
    Returns a dictionary with the inventory for target
    """
    full_inv_path = os.path.join(search_path, inventory_path)

    inv_target = inventory_reclass(full_inv_path)["nodes"][target]

    return inv_target


@memoize
def inventory_reclass(inventory_path):
    """
    Runs a reclass inventory in inventory_path
    (same output as running ./reclass.py -b streams/ --inventory)
    Will attempt to read reclass config from 'reclass-config.yml' otherwise
    it will failback to the default config.
    Returns a reclass style dictionary
    """

    reclass_config = {'storage_type': 'yaml_fs',
                      'inventory_base_uri': inventory_path,
                      'nodes_uri': os.path.join(inventory_path, 'targets'),
                      'classes_uri': os.path.join(inventory_path, 'classes')
                     }

    try:
        cfg_file = os.path.join(inventory_path, 'reclass-config.yml')
        with open(cfg_file) as reclass_cfg:
            reclass_config = yaml.safe_load(reclass_cfg)
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

    storage = reclass.get_storage(reclass_config['storage_type'], reclass_config['nodes_uri'],
                                  reclass_config['classes_uri'], default_environment='base')
    class_mappings = reclass_config.get('class_mappings')  # this defaults to None (disabled)
    _reclass = reclass.core.Core(storage, class_mappings)

    inv = _reclass.inventory()

    logger.debug("reclass inventory: %s", inv)
    return inv
