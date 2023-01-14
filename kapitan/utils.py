"random utils"
# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import print_function

import collections
import json
import logging
import magic
import math
import os
import re
import stat
import sys
import tarfile
import traceback
from collections import Counter, defaultdict
from distutils.dir_util import mkpath
from distutils.errors import DistutilsFileError
from distutils.file_util import _copy_file_contents
from functools import lru_cache, wraps
from hashlib import sha256
from zipfile import ZipFile

import jinja2
import requests
import yaml

from kapitan import cached, defaults
from kapitan.errors import CompileError
from kapitan.inputs.jinja2_filters import load_jinja2_filters, load_jinja2_filters_from_file
from kapitan.version import VERSION

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
        _kwargs = {
            k: json.dumps(v, sort_keys=True) if type(v) in (list, dict) else v for k, v in kwargs.items()
        }
        return cached_function(*_args, **_kwargs)

    lru_decorator.cache_info = cached_function.cache_info
    lru_decorator.cache_clear = cached_function.cache_clear
    return lru_decorator


class termcolor:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


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


def _jinja_error_info(trace_data):
    """Extract jinja2 templating related frames from traceback data"""
    try:
        return [x for x in trace_data if x[2] in ("top-level template code", "template", "<module>")][-1]
    except IndexError:
        pass


def render_jinja2_file(name, context, jinja2_filters=defaults.DEFAULT_JINJA2_FILTERS_PATH, search_paths=None):
    """Render jinja2 file name with context"""
    path, filename = os.path.split(name)
    search_paths = [path or "./"] + (search_paths or [])
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(search_paths),
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=["jinja2.ext.do"],
    )
    load_jinja2_filters(env)
    load_jinja2_filters_from_file(env, jinja2_filters)
    try:
        return env.get_template(filename).render(context)
    except jinja2.TemplateError as e:
        # Exception misses the line number info. Retreive it from traceback
        err_info = _jinja_error_info(traceback.extract_tb(sys.exc_info()[2]))
        raise CompileError(f"Jinja2 TemplateError: {e}, at {err_info[0]}:{err_info[1]}")


def render_jinja2(path, context, jinja2_filters=defaults.DEFAULT_JINJA2_FILTERS_PATH, search_paths=None):
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
            if f.startswith("."):
                logger.debug("render_jinja2: ignoring file %s", f)
                continue
            render_path = os.path.join(root, f)
            logger.debug("render_jinja2 rendering %s", render_path)
            # get subpath and filename, strip any leading/trailing /
            name = render_path[len(os.path.commonprefix([root, path])) :].strip("/")
            try:
                rendered[name] = {
                    "content": render_jinja2_file(
                        render_path, context, jinja2_filters=jinja2_filters, search_paths=search_paths
                    ),
                    "mode": file_mode(render_path),
                }
            except Exception as e:
                raise CompileError(f"Jinja2 error: failed to render {render_path}: {e}")

    return rendered


def file_mode(name):
    """Returns mode for file name"""
    st = os.stat(name)
    return stat.S_IMODE(st.st_mode)


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


def multiline_str_presenter(dumper, data):
    """
    Configures yaml for dumping multiline strings with given style.
    By default, strings are getting dumped with style='"'.
    Ref: https://github.com/yaml/pyyaml/issues/240#issuecomment-1018712495
    """
    # get parsed args from cached.py
    compile_args = cached.args.get("compile", None)
    style = None
    if compile_args:
        style = compile_args.yaml_multiline_string_style

    # check for inventory args too
    inventory_args = cached.args.get("inventory", None)
    if inventory_args:
        style = inventory_args.multiline_string_style

    if style == "literal":
        style = "|"
    elif style == "folded":
        style = ">"
    else:
        style = '"'
    if data.count("\n") > 0:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


PrettyDumper.add_representer(str, multiline_str_presenter)


def null_presenter(dumper, data):
    """Configures yaml for omitting value from null-datatype"""
    # get parsed args from cached.py
    compile_args = cached.args.get("compile", None)
    flag_value = None
    if compile_args:
        flag_value = compile_args.yaml_dump_null_as_empty

    if flag_value:
        return dumper.represent_scalar("tag:yaml.org,2002:null", "")
    else:
        return dumper.represent_scalar("tag:yaml.org,2002:null", "null")


PrettyDumper.add_representer(type(None), null_presenter)


def flatten_dict(d, parent_key="", sep="."):
    """Flatten nested elements in a dictionary"""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.abc.MutableMapping):
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
                if "*" in keys[0]:
                    key_lower = keys[0].replace("*", "").lower()
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

                            if item is not None:
                                return item

    return value


def searchvar(args):
    """Show all inventory files where a given reclass variable is declared"""
    output = []
    maxlength = 0
    keys = args.searchvar.split(".")
    for full_path in list_all_paths(args.inventory_path):
        if full_path.endswith(".yml") or full_path.endswith(".yaml"):
            with open(full_path, "r") as fd:
                data = yaml.load(fd, Loader=YamlLoader)
                value = deep_get(data, keys)
                if value is not None:
                    output.append((full_path, value))
                    if len(full_path) > maxlength:
                        maxlength = len(full_path)
    if args.pretty_print:
        for i in output:
            print(i[0])
            for line in yaml.dump(i[1], default_flow_style=False).splitlines():
                print("    ", line)
            print()
    else:
        for i in output:
            print("{0!s:{length}} {1!s}".format(*i, length=maxlength + 2))


def directory_hash(directory):
    """Return the sha256 hash for the file contents of a directory"""
    if not os.path.exists(directory):
        raise IOError(f"utils.directory_hash failed, {directory} dir doesn't exist")

    if not os.path.isdir(directory):
        raise IOError(f"utils.directory_hash failed, {directory} is not a directory")

    try:
        hash = sha256()
        for root, _, files in sorted(os.walk(directory)):
            for names in sorted(files):
                file_path = os.path.join(root, names)
                try:
                    with open(file_path, "r") as f:
                        file_hash = sha256(f.read().encode("UTF-8"))
                        hash.update(file_hash.hexdigest().encode("UTF-8"))
                except Exception as e:
                    if isinstance(e, UnicodeDecodeError):
                        with open(file_path, "rb") as f:
                            binary_file_hash = sha256(f.read())
                            hash.update(binary_file_hash.hexdigest().encode("UTF-8"))
                    else:
                        raise CompileError(f"utils.directory_hash failed to open {file_path}: {e}")
    except Exception as e:
        raise CompileError(f"utils.directory_hash failed: {e}")

    return hash.hexdigest()


def dictionary_hash(dict):
    """Return the sha256 hash for dict"""
    return sha256(json.dumps(dict, sort_keys=True).encode("UTF-8")).hexdigest()


def get_entropy(s):
    """Computes and returns the Shannon Entropy for string 's'"""
    length = float(len(s))
    # https://en.wiktionary.org/wiki/Shannon_entropy
    entropy = -sum(count / length * math.log(count / length, 2) for count in Counter(s).values())
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
            print(f"{termcolor.WARNING}Current version: {VERSION}")
            print(f"Version in .kapitan: {dot_kapitan_version}{termcolor.ENDC}\n")

            # If .kapitan version is greater than current version
            if result == "greater":
                print(f"Upgrade kapitan to '{dot_kapitan_version}' in order to keep results consistent:\n")
            # If .kapitan version is lower than current version
            elif result == "lower":
                print(f"Option 1: You can update the version in .kapitan to '{VERSION}' and recompile\n")
                print(
                    f"Option 2: Downgrade kapitan to '{dot_kapitan_version}' in order to keep results consistent:\n"
                )

            print(f"Docker: docker pull kapicorp/kapitan:{dot_kapitan_version}")
            print(f"Pip (user): pip3 install --user --upgrade kapitan=={dot_kapitan_version}\n")
            print("Check https://github.com/kapicorp/kapitan#quickstart for more info.\n")
            print(
                "If you know what you're doing, you can skip this check by adding '--ignore-version-check'."
            )
            sys.exit(1)
    except KeyError:
        pass


def search_target_token_paths(target_secrets_path, targets):
    """
    returns dict of target and their secret token paths (e.g ?{[gpg/gkms/awskms]:path/to/secret}) in target_secrets_path
    targets is a set of target names used to lookup targets in target_secrets_path
    directory should be structured as follow ./refs/${target_name}/file
    """
    target_files = defaultdict(list)
    for full_path in list_all_paths(target_secrets_path):
        secret_path = full_path[len(target_secrets_path) + 1 :]
        target_name = secret_path.split("/")[0]
        if target_name in targets and os.path.isfile(full_path):
            with open(full_path) as fp:
                obj = yaml.load(fp, Loader=YamlLoader)
                try:
                    secret_type = obj["type"]
                except KeyError:
                    # Backwards compatible with gpg secrets that didn't have type in yaml
                    secret_type = "gpg"
                secret_path = f"?{{{secret_type}:{secret_path}}}"
            logger.debug("search_target_token_paths: found %s", secret_path)
            target_files[target_name].append(secret_path)
    return target_files


def make_request(source):
    """downloads the http file at source and returns it's content"""
    r = requests.get(source)
    if r.ok:
        return r.content, r.headers["Content-Type"]
    else:
        r.raise_for_status()
    return None, None


def unpack_downloaded_file(file_path, output_path, content_type):
    """unpacks files of various MIME type and stores it to the output_path"""

    if content_type == None or content_type == "application/octet-stream":
        if re.search(r"^Zip archive data.*", magic.from_file(file_path)):
            content_type = "application/zip"

    if content_type == "application/x-tar":
        tar = tarfile.open(file_path)
        tar.extractall(path=output_path)
        tar.close()
        is_unpacked = True
    elif content_type == "application/zip":
        zfile = ZipFile(file_path)
        zfile.extractall(output_path)
        zfile.close()
        is_unpacked = True
    elif content_type in [
        "application/gzip",
        "application/octet-stream",
        "application/x-gzip",
        "application/x-compressed",
        "application/x-compressed-tar",
    ]:
        if re.search(r"(\.tar\.gz|\.tgz)$", file_path):
            tar = tarfile.open(file_path)
            tar.extractall(path=output_path)
            tar.close()
            is_unpacked = True
        else:
            extension = re.findall(r"\..*$", file_path)[0]
            logger.debug("File extension %s not suported", extension)
            is_unpacked = False
    else:
        logger.debug("Content type %s not suported", content_type)
        is_unpacked = False
    return is_unpacked


def safe_copy_file(src, dst):
    """Copy a file from 'src' to 'dst'.

    Similar to distutils.file_util.copy_file except
    if the file exists in 'dst' it's not clobbered
    or overwritten.

    returns a tupple (src, val)
    file not copied if val = 0 else 1
    """

    if not os.path.isfile(src):
        raise DistutilsFileError("Can't copy {}: doesn't exist or is not a regular file".format(src))

    if os.path.isdir(dst):
        dir = dst
        dst = os.path.join(dst, os.path.basename(src))
    else:
        dir = os.path.dirname(dst)

    if os.path.isfile(dst):
        logger.warning("Not updating %s (file already exists)", dst)
        return (dst, 0)
    _copy_file_contents(src, dst)
    logger.debug("Copied %s to %s", src, dir)
    return (dst, 1)


def safe_copy_tree(src, dst):
    """Recursively copies the 'src' directory tree to 'dst'

    Both 'src' and 'dst' must be directories.
    similar to distutil.dir_util.copy_tree except
    it doesn't overwite an existing file and doesn't
    copy any file starting with "."

    Returns a list of copied file paths.
    """
    if not os.path.isdir(src):
        raise DistutilsFileError("Cannot copy tree {}: not a directory".format(src))
    try:
        names = os.listdir(src)
    except OSError as e:
        raise DistutilsFileError("Error listing files in {}: {}".format(src, e.strerror))

    mkpath(dst)
    outputs = []

    for name in names:
        src_name = os.path.join(src, name)
        dst_name = os.path.join(dst, name)

        if name.startswith("."):
            logger.debug("Not copying %s", src_name)
            continue
        if os.path.isdir(src_name):
            outputs.extend(safe_copy_tree(src_name, dst_name))

        else:
            safe_copy_file(src_name, dst_name)
            outputs.append(dst_name)

    return outputs
