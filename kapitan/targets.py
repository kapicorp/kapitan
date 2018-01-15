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
import hashlib
import json
import re
import shutil
from functools import partial
import multiprocessing
import traceback
import tempfile
import jsonschema
import yaml

from kapitan.resources import search_imports, resource_callbacks, inventory
from kapitan.utils import jsonnet_file, jsonnet_prune, render_jinja2_dir, PrettyDumper
from kapitan.secrets import secret_gpg_raw_read, secret_token_from_tag, secret_token_attributes
from kapitan.secrets import SECRET_TOKEN_TAG_PATTERN, secret_gpg_read
from kapitan.errors import KapitanError

logger = logging.getLogger(__name__)

def compile_targets(target_files, search_path, output_path, parallel, **kwargs):
    """
    Loads files in target_files and runs compile_target_file() on a
    multiprocessing pool with parallel number of processes.
    kwargs are passed to compile_target_file()
    """
    # temp_path will hold compiled items
    temp_path = tempfile.mkdtemp(suffix='.kapitan')
    pool = multiprocessing.Pool(parallel)
    worker = partial(compile_target_file, search_path=search_path, output_path=temp_path, **kwargs)
    try:
        pool.map(worker, target_files)
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        # on success, copy temp_path into output_path
        shutil.copytree(temp_path, output_path)
        logger.debug("Copied %s into %s", temp_path, output_path)
    except Exception as e:
        # if compile worker fails, terminate immediately
        pool.terminate()
        pool.join()
        logger.debug("Compile pool terminated")
        # only print traceback for errors we don't know about
        if not isinstance(e, KapitanError):
            logger.error("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            traceback.print_exc()
    finally:
        shutil.rmtree(temp_path)
        logger.debug("Removed %s", temp_path)

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
                compile_jinja2(compile_path_sp, ctx, _output_path, **kwargs)
            else:
                raise IOError("Path not found in search_path: %s" % obj["path"])
    logger.info("Compiled %s", target_file)


def compile_jinja2(path, context, output_path, **kwargs):
    """
    Write items in path as jinja2 rendered files to output_path.
    kwargs:
        secrets_path: default None, set to access secrets backend
        secrets_reveal: default False, set to reveal secrets on compile
        gpg_obj: default None
    """
    secrets_path = kwargs.get('secrets_path', None)
    secrets_reveal = kwargs.get('secrets_reveal', False)
    gpg_obj = kwargs.get('gpg_obj', None)

    for item_key, item_value in render_jinja2_dir(path, context).iteritems():
        full_item_path = os.path.join(output_path, item_key)
        try:
            os.makedirs(os.path.dirname(full_item_path))
        except OSError as ex:
            # If directory exists, pass
            if ex.errno == errno.EEXIST:
                pass
        with CompiledFile(full_item_path, mode="w", secrets_path=secrets_path,
                          secrets_reveal=secrets_reveal, gpg_obj=gpg_obj) as fp:
            fp.write(item_value["content"])
            mode = item_value["mode"]
            os.chmod(full_item_path, mode)
            logger.debug("Wrote %s with mode %.4o", full_item_path, mode)


def compile_jsonnet(file_path, output_path, search_path, ext_vars, **kwargs):
    """
    Write file_path (jsonnet evaluated) items as files to output_path.
    Set output to write as json or yaml
    search_path and ext_vars will be passed as paramenters to jsonnet_file()
    kwargs:
        output: default 'yaml', accepts 'json'
        prune: default True, accepts False
        secrets_path: default None, set to access secrets backend
        secrets_reveal: default False, set to reveal secrets on compile
        gpg_obj: default None
    """
    _search_imports = lambda cwd, imp: search_imports(cwd, imp, search_path)
    json_output = jsonnet_file(file_path, import_callback=_search_imports,
                               native_callbacks=resource_callbacks(search_path),
                               ext_vars=ext_vars)

    output = kwargs.get('output', 'yaml')
    prune = kwargs.get('prune', True)
    secrets_path = kwargs.get('secrets_path', None)
    secrets_reveal = kwargs.get('secrets_reveal', False)
    gpg_obj = kwargs.get('gpg_obj', None)

    if prune:
        json_output = jsonnet_prune(json_output)
        logger.debug("Pruned output for: %s", file_path)
    for item_key, item_value in json.loads(json_output).iteritems():
        # write each item to disk
        if output == 'json':
            file_path = os.path.join(output_path, '%s.%s' % (item_key, output))
            with CompiledFile(file_path, mode="w", secrets_path=secrets_path,
                              secrets_reveal=secrets_reveal, gpg_obj=gpg_obj) as fp:
                json.dump(item_value, fp, indent=4, sort_keys=True)
                logger.debug("Wrote %s", file_path)
        elif output == 'yaml':
            file_path = os.path.join(output_path, '%s.%s' % (item_key, "yml"))
            with CompiledFile(file_path, mode="w", secrets_path=secrets_path,
                              secrets_reveal=secrets_reveal, gpg_obj=gpg_obj) as fp:
                yaml.dump(item_value, stream=fp, Dumper=PrettyDumper, default_flow_style=False)
                logger.debug("Wrote %s", file_path)
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

class CompilingFile(object):
    def __init__(self, context, fp, **kwargs):
        self.fp = fp
        self.kwargs = kwargs

    def hash_token_tag(self, token_tag):
        """
        suffixes a secret's hash to its tag:
        e.g:
        ?{gpg:app1/secret/1} gets replaced with
        ?{gpg:app1/secret/1:deadbeef}
        """
        secrets_path = self.kwargs.get("secrets_path", None)
        if secrets_path is None:
            raise ValueError("secrets_path not set")
        token = secret_token_from_tag(token_tag)
        secret_raw_obj = secret_gpg_raw_read(secrets_path, token)
        backend, token_path = secret_token_attributes(token)
        sha256 = hashlib.sha256("%s%s" % (token_path, secret_raw_obj["data"])).hexdigest()
        sha256 = sha256[:8]
        return "?{%s:%s:%s}" % (backend, token_path, sha256)

    def reveal_token_tag(self, token_tag):
        "reveal token_tag"
        secrets_path = self.kwargs.get("secrets_path", None)
        gpg_obj = self.kwargs.get("gpg_obj", None)
        if secrets_path is None:
            raise ValueError("secrets_path not set")
        if gpg_obj is None:
            raise ValueError("secrets_path not set")

        token = secret_token_from_tag(token_tag)
        return secret_gpg_read(gpg_obj, secrets_path, token)


    def sub_token_compiled(self, data):
        "find and replace tokens with hashed tokens in data"
        def _hash_token_tag(match_obj):
            token_tag, _ = match_obj.groups()
            return self.hash_token_tag(token_tag)

        return re.sub(SECRET_TOKEN_TAG_PATTERN, _hash_token_tag, data)

    def sub_token_reveal(self, data):
        "find and reveal token tags in data"
        def _reveal_token_tag(match_obj):
            token_tag, _ = match_obj.groups()
            return self.reveal_token_tag(token_tag)

        return re.sub(SECRET_TOKEN_TAG_PATTERN, _reveal_token_tag, data)

    def write(self, data):
        secrets_reveal = self.kwargs.get('secrets_reveal', False)
        if secrets_reveal:
            self.fp.write(self.sub_token_reveal(data))
        else:
            self.fp.write(self.sub_token_compiled(data))

class CompiledFile(object):
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.fp = None

    def __enter__(self):
        mode = self.kwargs.get("mode", "r")
        self.fp = open(self.name, mode)
        return CompilingFile(self, self.fp, **self.kwargs)

    def __exit__(self, *args):
        self.fp.close()
