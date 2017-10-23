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

"kapitan targets"

import logging
import os
import errno
import json
import re
import shutil
import jsonschema
import yaml

from kapitan.resources import search_imports, resource_callbacks, inventory
from kapitan.utils import jsonnet_file, jsonnet_prune, render_jinja2_dir, PrettyDumper

logger = logging.getLogger(__name__)


def compile_target_file(target_file, search_path, output_path, **kwargs):
    """
    Loads target file, compiles file (by scanning search_path)
    and writes to output_path
    """
    target_obj = load_target(target_file)
    target_name = target_obj["vars"]["target"]
    compile_obj = target_obj["compile"]
    ext_vars = target_obj["vars"]

    for obj in compile_obj:
        if obj["type"] == "jsonnet":
            compile_file_sp = os.path.join(search_path, obj["path"])
            if os.path.exists(compile_file_sp):
                _output_path = os.path.join(output_path, target_name, obj["name"])
                update_output_path_dirs(_output_path)
                logger.debug("Compiling %s", compile_file_sp)
                compile_jsonnet(compile_file_sp, _output_path, search_path,
                                ext_vars, output=obj["output"], **kwargs)
            else:
                raise IOError("Path not found in search_path: %s" % obj["path"])

        if obj["type"] == "jinja2":
            compile_path_sp = os.path.join(search_path, obj["path"])
            if os.path.exists(compile_path_sp):
                _output_path = os.path.join(output_path, target_name, obj["name"])
                update_output_path_dirs(_output_path)
                # copy ext_vars to dedicated jinja2 context so we can update it
                ctx = ext_vars.copy()
                ctx["inventory"] = inventory(search_path, target_name)
                ctx["inventory_global"] = inventory(search_path, None)
                compile_jinja2(compile_path_sp, ctx, _output_path)
            else:
                raise IOError("Path not found in search_path: %s" % obj["path"])


def compile_jinja2(path, context, output_path):
    """
    Write items in path as jinja2 rendered files to output_path.
    """
    for item_key, item_value in render_jinja2_dir(path, context).iteritems():
        full_item_path = os.path.join(output_path, item_key)
        try:
            os.makedirs(os.path.dirname(full_item_path))
        except OSError as ex:
            # If directory exists, pass
            if ex.errno == errno.EEXIST:
                pass
        with open(full_item_path, 'w') as fp:
            fp.write(item_value["content"])
            mode = item_value["mode"]
            os.chmod(full_item_path, mode)
            logger.info("Wrote %s with mode %.4o", full_item_path, mode)


def compile_jsonnet(file_path, output_path, search_path, ext_vars, **kwargs):
    """
    Write file_path (jsonnet evaluated) items as files to output_path.
    Set output to write as json or yaml
    search_path and ext_vars will be passed as paramenters to jsonnet_file()
    kwargs:
        output: default 'yaml', accepts 'json'
        prune: default True, accepts False
    """
    _search_imports = lambda cwd, imp: search_imports(cwd, imp, search_path)
    json_output = jsonnet_file(file_path, import_callback=_search_imports,
                               native_callbacks=resource_callbacks(search_path),
                               ext_vars=ext_vars)

    output = kwargs.get('output', 'yaml')
    prune = kwargs.get('prune', True)

    if prune:
        json_output = jsonnet_prune(json_output)
        logger.debug("Pruned output")
    for item_key, item_value in json.loads(json_output).iteritems():
        # write each item to disk
        if output == 'json':
            file_path = os.path.join(output_path, '%s.%s' % (item_key, output))
            with open(file_path, 'w') as fp:
                json.dump(item_value, fp, indent=4, sort_keys=True)
                logger.info("Wrote %s", file_path)
        elif output == 'yaml':
            file_path = os.path.join(output_path, '%s.%s' % (item_key, "yml"))
            with open(file_path, 'w') as fp:
                yaml.dump(item_value, stream=fp, Dumper=PrettyDumper, default_flow_style=False)
                logger.info("Wrote %s", file_path)
        else:
            raise ValueError('output is neither "json" or "yaml"')


def update_output_path_dirs(output_path):
    """
    Attempt to re/create (nested) directories
    """
    try:
        os.makedirs(output_path)
    except OSError as ex:
        # If directory exists, remove and recreate
        if ex.errno == errno.EEXIST:
            shutil.rmtree(output_path)
            logger.debug("Deleted %s", output_path)
            os.makedirs(output_path)
            logger.debug("Re-created %s", output_path)


def load_target(target_file):
    """
    Loads and validates a target_file name
    Format of the target file is determined by its extention (.json, .yml, .yaml)
    Returns a dict object if target is valid
    Otherwise raises ValidationError
    """
    schema = {
        "type": "object",
        "properties": {
            "version": {"type": "number"},
            "vars": {"type": "object"},
            "compile": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "path": {"type": "string"},
                        "output": {"type": "string"},
                    },
                    "required": ["type", "name"],
                    "minItems": 1,
                }
            },
        },
        "required": ["version", "compile"],
    }

    bname = os.path.basename(target_file)

    if re.match(r".+\.json$", bname):
        with open(target_file) as fp:
            target_obj = json.load(fp)
            jsonschema.validate(target_obj, schema)
            logger.debug("Target file %s is valid", target_file)

            return target_obj
    if re.match(r".+\.(yaml|yml)$", bname):
        with open(target_file) as fp:
            target_obj = yaml.safe_load(fp)
            jsonschema.validate(target_obj, schema)
            logger.debug("Target file %s is valid", target_file)

            return target_obj
