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

"random utils"
import functools
from hashlib import sha256
import logging
import os
import stat
import jinja2
import _jsonnet as jsonnet
import collections
import yaml


logger = logging.getLogger(__name__)

def normalise_join_path(dirname, path):
    "Join dirname with path and return in normalised form"
    logger.debug(os.path.normpath(os.path.join(dirname, path)))
    return os.path.normpath(os.path.join(dirname, path))


def render_jinja2_template(content, context):
    "Render jinja2 content with context"
    return jinja2.Template(content, undefined=jinja2.StrictUndefined).render(context)

def jinja2_sha256_hex_filter(string):
    "Returns hex digest for string"
    return sha256(string).hexdigest()

def render_jinja2_file(name, context):
    "Render jinja2 file name with context"
    path, filename = os.path.split(name)
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(path or './'),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters['sha256'] = jinja2_sha256_hex_filter
    return env.get_template(filename).render(context)


def render_jinja2_dir(path, context):
    """
    Render files in path with context
    Returns a dict where the is key is the filename (with subpath)
    and value is a dict with content and mode
    Empty paths will not be rendered
    """
    rendered = {}
    for root, _, files in os.walk(path):
        for f in files:
            render_path = os.path.join(root, f)
            logger.debug("render_jinja2_dir rendering %s with context %s",
                         render_path, context)
            # get subpath and filename, strip any leading/trailing /
            name = render_path[len(os.path.commonprefix([root, path])):].strip('/')
            rendered[name] = {"content": render_jinja2_file(render_path, context),
                              "mode": file_mode(render_path)
                             }
    return rendered


def file_mode(name):
    "Returns mode for file name"
    st = os.stat(name)
    return stat.S_IMODE(st.st_mode)

def jsonnet_file(file_path, **kwargs):
    """
    Evaluate file_path jsonnet file.
    kwargs are documented in http://jsonnet.org/implementation/bindings.html
    """
    return jsonnet.evaluate_file(file_path, **kwargs)

def jsonnet_prune(jsonnet_str):
    "Returns a pruned jsonnet_str"
    return jsonnet.evaluate_snippet("snippet", "std.prune(%s)" % jsonnet_str)

def memoize(obj):
    """
    Decorator that will cache a function's return value should it be called
    with the same arguments.
    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        "checks if args are memoizible"
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]
    return memoizer


class PrettyDumper(yaml.SafeDumper):
    '''
    Increases indent of nested lists.
    By default, they are indendented at the same level as the key on the previous line
    More info on https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation
    '''
    def increase_indent(self, flow=False, indentless=False):
        return super(PrettyDumper, self).increase_indent(flow, False)


def flatten_dict(d, parent_key='', sep='.'):
    '''
    Flatten nested elements in a dictionary
    '''
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def searchvar(flat_var, inventory_path):
    '''
    show all inventory files where a given reclass variable is declared
    '''

    def deep_get(x, keys):
        if type(x) is dict:
            try:
                return deep_get(x[keys[0]], keys[1:])
            except (IndexError, KeyError):
                pass
        else:
            if len(keys) == 0:
                return x
            else:
                return None

    output = []
    maxlenght = 0
    keys = flat_var.split(".")
    for root, dirs, files in os.walk(inventory_path):
        for file in files:
            if file.endswith(".yml"):
                filename = os.path.join(root, file)
                fd = open(filename, 'r')
                data = yaml.safe_load(fd)
                value = deep_get(data, keys)
                if value is not None:
                    output.append((filename, value))
                    if len(filename) > maxlenght:
                        maxlenght = len(filename)
                fd.close()
    for i in output:
        print('{0!s:{l}} {1!s}'.format(*i, l=maxlenght + 2))

