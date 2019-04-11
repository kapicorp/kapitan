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

import yaml
import base64
import glob
import os
import datetime
import time
import re
import types
import logging

from six import string_types
from random import Random, shuffle
from importlib import util

from kapitan.errors import CompileError
from kapitan import utils

logger = logging.getLogger(__name__)

#default path from where user defined custom filters are read
default_jinja2_filters_path = os.path.join('lib', 'jinja2_filters.py')


def load_jinja2_filters(env):
    """Load Jinja2 custom filters into env"""
    env.filters['sha256'] = utils.sha256_string
    env.filters['b64encode'] = base64_encode
    env.filters['b64decode'] = base64_decode
    env.filters['yaml'] = to_yaml
    env.filters['fileglob'] = fileglob
    env.filters['bool'] = to_bool
    env.filters['to_datetime'] = to_datetime
    env.filters['strftime'] = strftime
    env.filters['regex_replace'] = regex_replace
    env.filters['regex_escape'] = regex_escape
    env.filters['regex_search'] = regex_search
    env.filters['regex_findall'] = regex_findall
    env.filters['ternary'] = ternary
    env.filters['shuffle'] = randomize_list


def load_module_from_path(env, path):
    """
    Loads a python module from provided path and adds it to jinja2 environment
    filter name is same as that of function
    """
    try:
        module_name = os.path.basename(path).split('.')[0]
        custom_filter_spec = util.spec_from_file_location(module_name, path)
        custom_filter_module = util.module_from_spec(custom_filter_spec)
        custom_filter_spec.loader.exec_module(custom_filter_module)
        for function in dir(custom_filter_module):
            if isinstance(getattr(custom_filter_module, function),
                                    types.FunctionType):
                logger.debug("custom filter loaded from {}".format(path))
                env.filters[function] = getattr(custom_filter_module, function)
    except Exception as e:
        logger.debug("failed to find custom filter from path {}".format(path))
        raise IOError("jinja2 failed to render, could not load filter at {}: {}".format(path, e))


def load_jinja2_filters_from_file(env, jinja2_filters):
    """
    if filter points to default file and in case it doesn't exist then proceed silently, no error
    else try to load module (which will throw error in case of non existence of file)
    """
    jinja2_filters = os.path.normpath(jinja2_filters)
    if jinja2_filters == default_jinja2_filters_path:
        if not os.path.isfile(jinja2_filters):
            return 
    
    load_module_from_path(env, jinja2_filters)


# Custom filters
def base64_encode(string):
    return base64.b64encode(string.encode("UTF-8")).decode("UTF-8")


def base64_decode(string):
    return base64.b64decode(string).decode("UTF-8")


def to_yaml(obj):
    return yaml.safe_dump(obj, default_flow_style=False)


# Following filters are from https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/filter/core.py
def fileglob(pathname):
    """return list of matched regular files for glob"""
    return [g for g in glob.glob(pathname) if os.path.isfile(g)]


def to_bool(a):
    """return a bool for the arg"""
    if a is None or isinstance(a, bool):
        return a
    if isinstance(a, string_types):
        a = a.lower()
    if a in ('yes', 'on', '1', 'true', 1):
        return True
    return False


def to_datetime(string, format="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(string, format)


def strftime(string_format, second=None):
    """return current date string for format. See https://docs.python.org/3/library/time.html#time.strftime for format"""
    if second is not None:
        try:
            second = int(second)
        except Exception:
            raise CompileError('Invalid value for epoch value ({})'.format(second))
    return time.strftime(string_format, time.localtime(second))


def regex_replace(value='', pattern='', replacement='', ignorecase=False):
    """Perform a `re.sub` returning a string"""
    if ignorecase:
        flags = re.I
    else:
        flags = 0
    _re = re.compile(pattern, flags=flags)
    return _re.sub(replacement, value)


def regex_escape(string):
    """Escape all regular expressions special characters from STRING."""
    return re.escape(string)


def regex_search(value, regex, *args, **kwargs):
    """Perform re.search and return the list of matches or a backref"""
    groups = list()
    for arg in args:
        if arg.startswith('\\g'):
            match = re.match(r'\\g<(\S+)>', arg).group(1)
            groups.append(match)
        elif arg.startswith('\\'):
            match = int(re.match(r'\\(\d+)', arg).group(1))
            groups.append(match)
        else:
            raise CompileError('Unknown argument')

    flags = 0
    if kwargs.get('ignorecase'):
        flags |= re.I
    if kwargs.get('multiline'):
        flags |= re.M

    match = re.search(regex, value, flags)
    if match:
        if not groups:
            return match.group()
        else:
            items = list()
            for item in groups:
                items.append(match.group(item))
            return items


def regex_findall(value, regex, multiline=False, ignorecase=False):
    """Perform re.findall and return the list of matches"""
    flags = 0
    if ignorecase:
        flags |= re.I
    if multiline:
        flags |= re.M
    return re.findall(regex, value, flags)


def ternary(value, true_val, false_val, none_val=None):
    """value ? true_val : false_val"""
    if value is None and none_val is not None:
        return none_val
    elif bool(value):
        return true_val
    else:
        return false_val


def randomize_list(mylist, seed=None):
    try:
        mylist = list(mylist)
        if seed:
            r = Random(seed)
            r.shuffle(mylist)
        else:
            shuffle(mylist)
    except Exception:
        pass
    return mylist
