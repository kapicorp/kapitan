#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
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

from __future__ import print_function

"random utils"

import logging
import os
import sys
import stat
import collections
import json
import jinja2
import _jsonnet as jsonnet
import yaml
import math
import base64
from collections import Counter, defaultdict
from functools import lru_cache, wraps
from hashlib import sha256

from kapitan.version import VERSION
from kapitan.errors import CompileError
from kapitan.inputs.jinja2_filters import load_jinja2_filters
import kapitan.cached as cached

logger = logging.getLogger(__name__)

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader


def fatal_error(message):
    "Logs error message, sys.exit(1)"
    logger.error(message)
    sys.exit(1)


def hashable_lru_cache(func):
    """Usable instead of lru_cache for functions using unhashable objects"""

    cache = lru_cache(maxsize=256)

    def deserialise(value):
        try:
            return json.loads(value)
        except Exception:
            logger.debug("hashable_lru_cache: %s not serialiseable, using generic lru_cache instead", value)
            return value

    def func_with_serialized_params(*args, **kwargs):
        _args = tuple([deserialise(arg) for arg in args])
        _kwargs = {k: deserialise(v) for k, v in kwargs.items()}
        return func(*_args, **_kwargs)

    cached_function = cache(func_with_serialized_params)

    @wraps(func)
    def lru_decorator(*args, **kwargs):
        _args = tuple([json.dumps(arg, sort_keys=True) if type(arg) in (list, dict) else arg for arg in args])
        _kwargs = {k: json.dumps(v, sort_keys=True) if type(v) in (list, dict) else v for k, v in kwargs.items()}
        return cached_function(*_args, **_kwargs)

    lru_decorator.cache_info = cached_function.cache_info
    lru_decorator.cache_clear = cached_function.cache_clear
    return lru_decorator


class termcolor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def normalise_join_path(dirname, path):
    """Join dirname with path and return in normalised form"""
    logger.debug(os.path.normpath(os.path.join(dirname, path)))
    return os.path.normpath(os.path.join(dirname, path))


@lru_cache(maxsize=256)
def render_jinja2_template(content, context):
    """Render jinja2 content with context"""
    return jinja2.Template(content, undefined=jinja2.StrictUndefined).render(context)


@lru_cache(maxsize=256)
def sha256_string(string):
    """Returns sha256 hex digest for string"""
    return sha256(string.encode("UTF-8")).hexdigest()


def render_jinja2_file(name, context):
    """Render jinja2 file name with context"""
    path, filename = os.path.split(name)
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(path or './'),
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=['jinja2.ext.do'],
    )
    load_jinja2_filters(env)
    return env.get_template(filename).render(context)


def render_jinja2(path, context):
    """
    Render files in path with context
    Returns a dict where the is key is the filename (with subpath)
    and value is a dict with content and mode
    Empty paths will not be rendered
    Path can be a single file or directory
    Ignores hidden files (.filename)
    """
    rendered = {}
    walk_root_files = []
    if os.path.isfile(path):
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        walk_root_files = [(dirname, None, [basename])]
    else:
        walk_root_files = os.walk(path)

    for root, _, files in walk_root_files:
        for f in files:
            if f.startswith('.'):
                logger.debug('render_jinja2: ignoring file %s', f)
                continue
            render_path = os.path.join(root, f)
            logger.debug("render_jinja2 rendering %s", render_path)
            # get subpath and filename, strip any leading/trailing /
            name = render_path[len(os.path.commonprefix([root, path])):].strip('/')
            try:
                rendered[name] = {
                    "content": render_jinja2_file(render_path, context),
                    "mode": file_mode(render_path)
                }
            except Exception as e:
                raise CompileError("Jinja2 error: failed to render {}: {}".format(render_path, e))

    return rendered


def file_mode(name):
    """Returns mode for file name"""
    st = os.stat(name)
    return stat.S_IMODE(st.st_mode)


def jsonnet_file(file_path, **kwargs):
    """
    Evaluate file_path jsonnet file.
    kwargs are documented in http://jsonnet.org/implementation/bindings.html
    """
    try:
        return jsonnet.evaluate_file(file_path, **kwargs)
    except Exception as e:
        raise CompileError("Jsonnet error: failed to compile {}:\n {}".format(file_path, e))


def prune_empty(d):
    """
    Remove empty lists and empty dictionaries from d
    (similar to jsonnet std.prune but faster)
    """
    if not isinstance(d, (dict, list)):
        return d

    if isinstance(d, list):
        if len(d) > 0:
            return [v for v in (prune_empty(v) for v in d) if v is not None]

    if isinstance(d, dict):
        if len(d) > 0:
            return {k: v for k, v in ((k, prune_empty(v)) for k, v in d.items()) if v is not None}


class PrettyDumper(yaml.SafeDumper):
    """
    Increases indent of nested lists.
    By default, they are indendented at the same level as the key on the previous line
    More info on https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation
    """
    def increase_indent(self, flow=False, indentless=False):
        return super(PrettyDumper, self).increase_indent(flow, False)


def flatten_dict(d, parent_key='', sep='.'):
    """Flatten nested elements in a dictionary"""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@hashable_lru_cache
def deep_get(dictionary, keys, previousKey=None):
    """Search recursively for 'keys' in 'dictionary' and return value, otherwise return None"""
    value = None
    if len(keys) > 0:
        value = dictionary.get(keys[0], None) if isinstance(dictionary, dict) else None

        if value:
            # If we are at the last key and we have a value, we are done
            if len(keys) == 1:
                return value

            # If we have more variables in the search chain and we don't have a dict, return not found
            if not isinstance(value, dict):
                return None

            # Recurse with next keys in the chain on the dict
            return deep_get(value, keys[1:], previousKey=keys[0])
        else:
            if isinstance(dictionary, dict):
                # If we find nothing, check for globbing, loop and match with dict keys
                if '*' in keys[0]:
                    key_lower = keys[0].replace('*', '').lower()
                    for dict_key in dictionary.keys():
                        if key_lower in dict_key.lower():
                            # If we're at the last key in the chain, return matched value
                            if len(keys) == 1:
                                return dictionary[dict_key]

                            # If we have more variables in the chain, continue recursion
                            return deep_get(dictionary[dict_key], keys[1:], previousKey=keys[0])

                if not previousKey:
                    # No previous keys in chain and no globbing, move down the dictionary and recurse
                    for v in dictionary.values():
                        if isinstance(v, dict):
                            item = None
                            if len(keys) > 1:
                                item = deep_get(v, keys, previousKey=keys[0])
                            else:
                                item = deep_get(v, keys)

                            if item:
                                return item

    return value


def searchvar(flat_var, inventory_path, pretty_print):
    """Show all inventory files where a given reclass variable is declared"""
    output = []
    maxlength = 0
    keys = flat_var.split(".")
    for full_path in list_all_paths(inventory_path):
        if full_path.endswith(".yml") or full_path.endswith(".yaml"):
            with open(full_path, 'r') as fd:
                data = yaml.load(fd, Loader=YamlLoader)
                value = deep_get(data, keys)
                if value is not None:
                    output.append((full_path, value))
                    if len(full_path) > maxlength:
                        maxlength = len(full_path)
    if pretty_print:
        for i in output:
            print(i[0])
            for line in yaml.dump(i[1], default_flow_style=False).splitlines():
                print("    ", line)
            print()
    else:
        for i in output:
            print('{0!s:{length}} {1!s}'.format(*i, length=maxlength + 2))


def directory_hash(directory):
    """Return the sha256 hash for the file contents of a directory"""
    if not os.path.exists(directory):
        raise IOError("utils.directory_hash failed, {} dir doesn't exist".format(directory))

    if not os.path.isdir(directory):
        raise IOError("utils.directory_hash failed, {} is not a directory".format(directory))

    try:
        hash = sha256()
        for root, _, files in sorted(os.walk(directory)):
            for names in sorted(files):
                file_path = os.path.join(root, names)
                try:
                    with open(file_path, 'r') as f:
                        file_hash = sha256(f.read().encode("UTF-8"))
                        hash.update(file_hash.hexdigest().encode("UTF-8"))
                except Exception as e:
                    if isinstance(e, UnicodeDecodeError):
                        with open(file_path, 'rb') as f:
                            binary_file_hash = sha256(f.read())
                            hash.update(binary_file_hash.hexdigest().encode("UTF-8"))
                    else:
                        raise CompileError("utils.directory_hash failed to open {}: {}".format(file_path, e))
    except Exception as e:
        raise CompileError("utils.directory_hash failed: {}".format(e))

    return hash.hexdigest()


def dictionary_hash(dict):
    """Return the sha256 hash for dict"""
    return sha256(json.dumps(dict, sort_keys=True).encode("UTF-8")).hexdigest()


def get_entropy(s):
    """Computes and returns the Shannon Entropy for string 's'"""
    length = float(len(s))
    # https://en.wiktionary.org/wiki/Shannon_entropy
    entropy = - sum(count / length * math.log(count / length, 2) for count in Counter(s).values())
    return round(entropy, 2)


def list_all_paths(folder):
    """Given a folder (string), returns a list with the full paths
       of every sub-folder/file.
    """
    for root, folders, files in os.walk(folder):
        for filename in folders + files:
            yield os.path.join(root, filename)


def dot_kapitan_config():
    """Returns the parsed YAML .kapitan file. Subsequent requests will be cached"""
    if not cached.dot_kapitan:
        if os.path.exists(".kapitan"):
            with open(".kapitan", "r") as f:
                cached.dot_kapitan = yaml.safe_load(f)

    return cached.dot_kapitan


def from_dot_kapitan(command, flag, default):
    """
    Returns the 'flag' for 'command' from .kapitan file. If failed, returns 'default'
    """
    kapitan_config = dot_kapitan_config()

    try:
        if kapitan_config[command]:
            flag_value = kapitan_config[command][flag]
            if flag_value:
                return flag_value
    except KeyError:
        pass

    return default


def compare_versions(v1_raw, v2_raw):
    """
    Parses v1_raw and v2_raw into versions and compares them
    Returns 'equal' if v1 == v2
    Returns 'greater' if v1 > v2
    Returns 'lower' if v1 < v2
    """
    v1 = v1_raw.replace("-rc", "")
    v2 = v2_raw.replace("-rc", "")
    v1_split = v1.split(".")
    v2_split = v2.split(".")
    min_range = min(len(v1_split), len(v2_split))

    for i in range(min_range):
        if v1_split[i] == v2_split[i]:
            continue
        if v1_split[i] > v2_split[i]:
            return "greater"
        if v1_split[i] < v2_split[i]:
            return "lower"

    if min_range > 2:
        v1_is_rc = "-rc" in v1_raw
        v2_is_rc = "-rc" in v2_raw

        if not v1_is_rc and v2_is_rc:
            return "greater"
        elif v1_is_rc and not v2_is_rc:
            return "lower"

    return "equal"


def check_version():
    """
    Checks the version in .kapitan is the same as the current version.
    If the version in .kapitan is greater, it will prompt to upgrade.
    If the version in .kapitan is lower, it will prompt to update .kapitan or downgrade.
    """
    kapitan_config = dot_kapitan_config()
    try:
        if kapitan_config and kapitan_config["version"]:
            dot_kapitan_version = str(kapitan_config["version"])
            result = compare_versions(dot_kapitan_version, VERSION)
            if result == "equal":
                return
            print("{}Current version: {}".format(termcolor.WARNING, VERSION))
            print("Version in .kapitan: {}{}\n".format(dot_kapitan_version, termcolor.ENDC))

            # If .kapitan version is greater than current version
            if result == "greater":
                print("Upgrade kapitan to '{}' in order to keep results consistent:\n".format(dot_kapitan_version))
            # If .kapitan version is lower than current version
            elif result == "lower":
                print("Option 1: You can update the version in .kapitan to '{}' and recompile\n".format(VERSION))
                print("Option 2: Downgrade kapitan to '{}' in order to keep results consistent:\n".format(dot_kapitan_version))

            print("Docker: docker pull deepmind/kapitan:{}".format(dot_kapitan_version))
            print("Pip (user): pip3 install --user --upgrade kapitan=={}\n".format(dot_kapitan_version))
            print("Check https://github.com/deepmind/kapitan#quickstart for more info.\n")
            print("If you know what you're doing, you can skip this check by adding '--ignore-version-check'.")
            sys.exit(1)
    except KeyError:
        pass


def search_target_token_paths(target_secrets_path, targets):
    """
    returns dict of target and their secret token paths (e.g ?{[gpg/gkms/awskms]:path/to/secret}) in target_secrets_path
    targets is a set of target names used to lookup targets in target_secrets_path
    """
    target_files = defaultdict(list)
    for full_path in list_all_paths(target_secrets_path):
        secret_path = full_path[len(target_secrets_path) + 1:]
        target_name = secret_path.split("/")[0]
        if target_name in targets and os.path.isfile(full_path):
            with open(full_path) as fp:
                obj = yaml.load(fp, Loader=YamlLoader)
                try:
                    secret_type = obj['type']
                except KeyError:
                    # Backwards compatible with gpg secrets that didn't have type in yaml
                    secret_type = "gpg"
                secret_path = "?{{{}:{}}}".format(secret_type, secret_path)
            logger.debug('search_target_token_paths: found %s', secret_path)
            target_files[target_name].append(secret_path)
    return target_files
