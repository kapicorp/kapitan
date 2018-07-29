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

"kapitan targets"

from six import string_types

import logging
import os
import errno
import hashlib
import ujson as json
import re
import shutil
import sys
from functools import partial
import multiprocessing
import traceback
import tempfile
import jsonschema
import yaml
import time

from kapitan.resources import search_imports, resource_callbacks, inventory, inventory_reclass
from kapitan.utils import jsonnet_file, prune_empty, render_jinja2, PrettyDumper, hashable_lru_cache
from kapitan.utils import directory_hash, dictionary_hash
from kapitan.secrets import secret_gpg_raw_read, secret_token_from_tag, secret_token_attributes
from kapitan.secrets import SECRET_TOKEN_TAG_PATTERN, secret_gpg_read
from kapitan.secrets import secret_gpg_exists, secret_gpg_write_function
from kapitan.errors import KapitanError, CompileError
from kapitan import cached

logger = logging.getLogger(__name__)


def compile_targets(inventory_path, search_paths, output_path, parallel, targets, **kwargs):
    """
    Searches and loads target files, and runs compile_target_file() on a
    multiprocessing pool with parallel number of processes.
    kwargs are passed to compile_target()
    """
    # temp_path will hold compiled items
    temp_path = tempfile.mkdtemp(suffix='.kapitan')

    generate_inv_cache_hashes(inventory_path, targets)

    changed_targets = targets
    if not kwargs.get('force_recompile') and not targets:
        changed_targets = get_changed_targets(inventory_path, output_path)
        logger.debug("Changed targets since last compilation: %s", changed_targets)
        if len(changed_targets) == 0:
            logger.info("No changes since last compilation.")
            return

    target_objs = load_target_inventory(inventory_path, changed_targets)

    pool = multiprocessing.Pool(parallel)
    # append "compiled" to output_path so we can safely overwrite it
    compile_path = os.path.join(output_path, "compiled")
    worker = partial(compile_target, search_paths=search_paths, compile_path=temp_path, **kwargs)

    try:
        if target_objs == []:
            logger.error("Error: no targets found")
            raise KapitanError("Error: no targets found")
        # compile_target() returns None on success
        # so p is only not None when raising an exception
        [p.get() for p in pool.imap_unordered(worker, target_objs) if p]

        if not os.path.exists(compile_path):
            os.makedirs(compile_path)

        # if '-t' is set on compile or only a few changed, only override selected targets
        if changed_targets:
            for target in changed_targets:
                compile_path_target = os.path.join(compile_path, target)
                temp_path_target = os.path.join(temp_path, target)

                if not os.path.exists(compile_path_target):
                    os.makedirs(compile_path_target)

                shutil.rmtree(compile_path_target)
                shutil.copytree(temp_path_target, compile_path_target)
                logger.debug("Copied %s into %s", temp_path_target, compile_path_target)
        # otherwise override all targets
        else:
            shutil.rmtree(compile_path)
            shutil.copytree(temp_path, compile_path)
            logger.debug("Copied %s into %s", temp_path, compile_path)

        # Save inventory and folders cache
        save_inv_cache(compile_path, targets)

    except Exception as e:
        # if compile worker fails, terminate immediately
        pool.terminate()
        pool.join()
        logger.debug("Compile pool terminated")
        # only print traceback for errors we don't know about
        if not isinstance(e, KapitanError):
            logger.error("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            traceback.print_exc()
        sys.exit(1)
    finally:
        shutil.rmtree(temp_path)
        logger.debug("Removed %s", temp_path)


def generate_inv_cache_hashes(inventory_path, targets):
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
    cached.inv_cache['inventory'] = {}
    cached.inv_cache['folder'] = {}

    if targets:
        for target in targets:
            cached.inv_cache['inventory'][target] = {}
            cached.inv_cache['inventory'][target]['classes'] = dictionary_hash(inv['nodes'][target]['classes'])
            cached.inv_cache['inventory'][target]['parameters'] = dictionary_hash(inv['nodes'][target]['parameters'])
    else:
        for target in inv['nodes']:
            cached.inv_cache['inventory'][target] = {}
            cached.inv_cache['inventory'][target]['classes'] = dictionary_hash(inv['nodes'][target]['classes'])
            cached.inv_cache['inventory'][target]['parameters'] = dictionary_hash(inv['nodes'][target]['parameters'])

            compile_obj = inv['nodes'][target]['parameters']['kapitan']['compile']
            for obj in compile_obj:
                for input_path in obj['input_paths']:
                    base_folder = os.path.dirname(input_path).split('/')[0]
                    if base_folder == '':
                        base_folder = os.path.basename(input_path).split('/')[0]

                    if base_folder not in cached.inv_cache['folder'].keys():
                        if os.path.exists(base_folder) and os.path.isdir(base_folder):
                            cached.inv_cache['folder'][base_folder] = directory_hash(base_folder)

                # Most commonly changed but not referenced in input_paths
                for common in ('lib', 'vendor', 'secrets'):
                    if common not in cached.inv_cache['folder'].keys():
                        if os.path.exists(common) and os.path.isdir(common):
                            cached.inv_cache['folder'][common] = directory_hash(common)


def get_changed_targets(inventory_path, output_path):
    """returns a list of targets that have changed since last compilation"""
    targets = []
    inv = inventory_reclass(inventory_path)

    saved_inv_cache = None
    saved_inv_cache_path = os.path.join(output_path, "compiled/.kapitan_cache")
    if os.path.exists(saved_inv_cache_path):
        with open(saved_inv_cache_path, "r") as f:
            try:
                saved_inv_cache = yaml.safe_load(f)
            except Exception as e:
                logger.error("Failed to load kapitan cache: %s", saved_inv_cache_path)

    targets_list = list(inv['nodes'])

    # If .kapitan_cache doesn't exist or failed to load, recompile all targets
    if not saved_inv_cache:
        return targets_list
    else:
        for key, hash in cached.inv_cache['folder'].items():
            try:
                if hash != saved_inv_cache['folder'][key]:
                    logger.debug("%s folder hash changed, recompiling all targets", key)
                    return targets_list
            except Exception as e:
                # Errors usually occur when saved_inv_cache doesn't contain a new folder
                # Recompile anyway to be safe
                return targets_list

        for target in targets_list:
            try:
                if cached.inv_cache['inventory'][target]['classes'] != saved_inv_cache['inventory'][target]['classes']:
                    logger.debug("classes hash changed in %s, recompiling", target)
                    targets.append(target)
                elif cached.inv_cache['inventory'][target]['parameters'] != saved_inv_cache['inventory'][target]['parameters']:
                    logger.debug("parameters hash changed in %s, recompiling", target)
                    targets.append(target)
            except Exception as e:
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
            except Exception as e:
                pass

            if saved_inv_cache:
                if 'inventory' not in saved_inv_cache:
                    saved_inv_cache['inventory'] = {}
            else:
                saved_inv_cache = {}
                saved_inv_cache['inventory'] = {}

            for target in targets:
                if target not in saved_inv_cache['inventory']:
                    saved_inv_cache['inventory'][target] = {}

                saved_inv_cache['inventory'][target]['classes'] = cached.inv_cache['inventory'][target]['classes']
                saved_inv_cache['inventory'][target]['parameters'] = cached.inv_cache['inventory'][target]['parameters']

            with open(inv_cache_path, "w") as f:
                logger.debug("Saved .kapitan_cache for targets: %s", targets)
                yaml.dump(saved_inv_cache, stream=f, default_flow_style=False)

        else:
            with open(inv_cache_path, "w") as f:
                logger.debug("Saved .kapitan_cache")
                yaml.dump(cached.inv_cache, stream=f, default_flow_style=False)


def load_target_inventory(inventory_path, targets):
    """retuns a list of target objects from the inventory"""
    target_objs = []
    inv = inventory_reclass(inventory_path)

    targets_list = inv['nodes']
    # if '-t' is set on compile, only loop through selected targets
    if targets:
        targets_list = targets

    for target_name in targets_list:
        try:
            target_obj = inv['nodes'][target_name]['parameters']['kapitan']
            valid_target_obj(target_obj)
            logger.debug("load_target_inventory: found valid kapitan target %s", target_name)
            target_objs.append(target_obj)
        except KeyError:
            logger.debug("load_target_inventory: target %s has no kapitan compile obj", target_name)
            pass

    return target_objs


def compile_target(target_obj, search_paths, compile_path, **kwargs):
    """Compiles target_obj and writes to compile_path"""
    start = time.time()

    ext_vars = target_obj["vars"]
    target_name = ext_vars["target"]
    compile_obj = target_obj["compile"]

    for obj in compile_obj:
        input_type = obj["input_type"]
        input_paths = obj["input_paths"]
        output_path = obj["output_path"]

        if input_type == "jsonnet":
            _compile_path = os.path.join(compile_path, target_name, output_path)
            # support writing to an already existent dir
            try:
                os.makedirs(_compile_path)
            except OSError as ex:
                # If directory exists, pass
                if ex.errno == errno.EEXIST:
                    pass

            output_type = obj["output_type"]  # output_type is mandatory in jsonnet
            for input_path in input_paths:
                jsonnet_file_found = False
                for path in search_paths:
                    compile_file_sp = os.path.join(path, input_path)
                    if os.path.exists(compile_file_sp):
                        jsonnet_file_found = True
                        logger.debug("Compiling %s", compile_file_sp)
                        try:
                            compile_jsonnet(compile_file_sp, _compile_path, search_paths, ext_vars,
                                            output=output_type, target_name=target_name, **kwargs)
                        except CompileError as e:
                            logger.error("Compile error: failed to compile target: %s", target_name)
                            raise e

                if not jsonnet_file_found:
                    logger.error("Compile error: %s for target: %s not found in " +
                                 "search_paths: %s", input_path, target_name, search_paths)
                    raise CompileError()

        if input_type == "jinja2":
            _compile_path = os.path.join(compile_path, target_name, output_path)
            # support writing to an already existent dir
            try:
                os.makedirs(_compile_path)
            except OSError as ex:
                # If directory exists, pass
                if ex.errno == errno.EEXIST:
                    pass
            for input_path in input_paths:
                jinja2_file_found = False
                for path in search_paths:
                    compile_path_sp = os.path.join(path, input_path)
                    if os.path.exists(compile_path_sp):
                        jinja2_file_found = True
                        # copy ext_vars to dedicated jinja2 context so we can update it
                        ctx = ext_vars.copy()
                        ctx["inventory"] = inventory(search_paths, target_name)
                        ctx["inventory_global"] = inventory(search_paths, None)
                        try:
                            compile_jinja2(compile_path_sp, ctx, _compile_path,
                                           target_name=target_name, **kwargs)
                        except CompileError as e:
                            logger.error("Compile error: failed to compile target: %s", target_name)
                            raise e

                if not jinja2_file_found:
                    logger.error("Compile error: %s for target: %s not found in " +
                                 "search_paths: %s", input_path, target_name, search_paths)
                    raise CompileError()

    logger.info("Compiled %s (%.2fs)", target_name, time.time() - start)


def compile_jinja2(path, context, compile_path, **kwargs):
    """
    Write items in path as jinja2 rendered files to compile_path.
    path can be either a file or directory.
    kwargs:
        secrets_path: default None, set to access secrets backend
        secrets_reveal: default False, set to reveal secrets on compile
        target_name: default None, set to current target being compiled
    """
    secrets_path = kwargs.get('secrets_path', None)
    secrets_reveal = kwargs.get('secrets_reveal', False)
    target_name = kwargs.get('target_name', None)

    for item_key, item_value in render_jinja2(path, context).items():
        full_item_path = os.path.join(compile_path, item_key)
        try:
            os.makedirs(os.path.dirname(full_item_path))
        except OSError as ex:
            # If directory exists, pass
            if ex.errno == errno.EEXIST:
                pass
        with CompiledFile(full_item_path, mode="w", secrets_path=secrets_path,
                          secrets_reveal=secrets_reveal, target_name=target_name) as fp:
            fp.write(item_value["content"])
            mode = item_value["mode"]
            os.chmod(full_item_path, mode)
            logger.debug("Wrote %s with mode %.4o", full_item_path, mode)


def compile_jsonnet(file_path, compile_path, search_paths, ext_vars, **kwargs):
    """
    Write file_path (jsonnet evaluated) items as files to compile_path.
    Set output to write as json or yaml
    search_paths and ext_vars will be passed as parameters to jsonnet_file()
    kwargs:
        output: default 'yaml', accepts 'json'
        prune: default False, accepts True
        secrets_path: default None, set to access secrets backend
        secrets_reveal: default False, set to reveal secrets on compile
        target_name: default None, set to current target being compiled
        indent: default 2
    """
    _search_imports = lambda cwd, imp: search_imports(cwd, imp, search_paths)
    json_output = jsonnet_file(file_path, import_callback=_search_imports,
                               native_callbacks=resource_callbacks(search_paths),
                               ext_vars=ext_vars)
    json_output = json.loads(json_output)

    output = kwargs.get('output', 'yaml')
    prune = kwargs.get('prune', False)
    secrets_path = kwargs.get('secrets_path', None)
    secrets_reveal = kwargs.get('secrets_reveal', False)
    target_name = kwargs.get('target_name', None)
    indent = kwargs.get('indent', 2)

    if prune:
        json_output = prune_empty(json_output)
        logger.debug("Pruned output for: %s", file_path)

    for item_key, item_value in json_output.items():
        # write each item to disk
        if output == 'json':
            file_path = os.path.join(compile_path, '%s.%s' % (item_key, output))
            with CompiledFile(file_path, mode="w", secrets_path=secrets_path,
                              secrets_reveal=secrets_reveal, target_name=target_name,
                              indent=indent) as fp:
                fp.write_json(item_value)
                logger.debug("Wrote %s", file_path)
        elif output == 'yaml':
            file_path = os.path.join(compile_path, '%s.%s' % (item_key, "yml"))
            with CompiledFile(file_path, mode="w", secrets_path=secrets_path,
                              secrets_reveal=secrets_reveal, target_name=target_name,
                              indent=indent) as fp:
                fp.write_yaml(item_value)
                logger.debug("Wrote %s", file_path)
        else:
            raise ValueError('output is neither "json" or "yaml"')


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
                    },
                    "required": ["input_type", "input_paths", "output_path"],
                    "minItems": 1,
                }
            },
        },
        "required": ["compile"],
    }

    return jsonschema.validate(target_obj, schema)


class CompilingFile(object):
    def __init__(self, context, fp, **kwargs):
        self.fp = fp
        self.kwargs = kwargs

    def write(self, data):
        """write data into file"""
        secrets_reveal = self.kwargs.get('secrets_reveal', False)
        if secrets_reveal:
            self.fp.write(self.sub_token_reveal_data(data))
        else:
            self.fp.write(self.sub_token_compiled_data(data))

    def write_yaml(self, obj):
        """recursively hash or reveal secrets and convert obj to yaml and write to file"""
        indent = self.kwargs.get('indent', 2)
        secrets_reveal = self.kwargs.get('secrets_reveal', False)
        if secrets_reveal:
            self.sub_token_reveal_obj(obj)
        else:
            self.sub_token_compiled_obj(obj)
        yaml.dump(obj, stream=self.fp, indent=indent, Dumper=PrettyDumper, default_flow_style=False)

    def write_json(self, obj):
        """recursively hash or reveal secrets and convert obj to json and write to file"""
        indent = self.kwargs.get('indent', 2)
        secrets_reveal = self.kwargs.get('secrets_reveal', False)
        if secrets_reveal:
            self.sub_token_reveal_obj(obj)
        else:
            self.sub_token_compiled_obj(obj)
        json.dump(obj, self.fp, indent=indent, escape_forward_slashes=False)

    def sub_token_compiled_obj(self, obj):
        """recursively find and replace tokens with hashed tokens in obj"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self.sub_token_compiled_obj(v)
        elif isinstance(obj, list):
            obj = list(map(self.sub_token_compiled_obj, obj))
        elif isinstance(obj, string_types):
            obj = self.sub_token_compiled_data(obj)

        return obj

    def sub_token_reveal_obj(self, obj):
        """recursively find and reveal token tags in data"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self.sub_token_reveal_obj(v)
        elif isinstance(obj, list):
            obj = list(map(self.sub_token_reveal_obj, obj))
        elif isinstance(obj, string_types):
            obj = self.sub_token_reveal_data(obj)

        return obj

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
        token, func = secret_token_from_tag(token_tag)
        secret_raw_obj = secret_gpg_raw_read(secrets_path, token)
        backend, token_path = secret_token_attributes(token)
        sha256 = hashlib.sha256("%s%s".encode("UTF-8") % (token_path.encode("UTF-8"),
                                                          secret_raw_obj["data"].encode("UTF-8"))).hexdigest()
        sha256 = sha256[:8]
        return "?{%s:%s:%s}" % (backend, token_path, sha256)

    def reveal_token_tag(self, token_tag):
        """reveal token_tag"""
        secrets_path = self.kwargs.get("secrets_path", None)
        if secrets_path is None:
            raise ValueError("secrets_path not set")

        token, func = secret_token_from_tag(token_tag)
        return secret_gpg_read(secrets_path, token)

    def sub_token_compiled_data(self, data):
        """find and replace tokens with hashed tokens in data"""
        def _hash_token_tag(match_obj):
            token_tag, token, func = match_obj.groups()
            _, token_path = secret_token_attributes(token)
            secrets_path = self.kwargs.get("secrets_path", None)
            if secrets_path is None:
                raise ValueError('secrets_path not set')

            # if token secret func is defined and secret does not exist
            # write secret from func eval
            if func and not secret_gpg_exists(secrets_path, token_path):
                logger.info("Creating secret for %s:%s ...", token_path, func)
                self.target_secret_func_write(token_path, func)

            return self.hash_token_tag(token_tag)

        return re.sub(SECRET_TOKEN_TAG_PATTERN, _hash_token_tag, data)

    def sub_token_reveal_data(self, data):
        """find and reveal token tags in data"""
        def _reveal_token_tag(match_obj):
            token_tag, _ = match_obj.groups()
            return self.reveal_token_tag(token_tag)

        return re.sub(SECRET_TOKEN_TAG_PATTERN, _reveal_token_tag, data)

    def target_secret_func_write(self, token_path, func):
        """write a target secret for token with data from func"""
        target_name = self.kwargs.get('target_name', None)
        secrets_path = self.kwargs.get('secrets_path', None)
        target_inv = cached.inv['nodes'].get(target_name, None)
        if target_name is None:
            raise ValueError('target_name not set')
        if target_inv is None:
            raise ValueError('target_inv not set')
        if secrets_path is None:
            raise ValueError('secrets_path not set')
        recipients = target_inv['parameters']['kapitan']['secrets']['recipients']

        secret_gpg_write_function(secrets_path, token_path, func, recipients)


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
