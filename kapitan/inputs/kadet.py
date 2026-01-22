#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextvars
import inspect
import json
import logging
import os
import sys
from functools import cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import kadet
from kadet import BaseModel, BaseObj, Dict

from kapitan import cached
from kapitan.errors import CompileError
from kapitan.inputs.base import InputType
from kapitan.inputs.cache import InputCache
from kapitan.inventory.model.input_types import KapitanInputTypeKadetConfig


# Set external kadet exception to kapitan.error.CompileError
kadet.ABORT_EXCEPTION_TYPE = CompileError

logger = logging.getLogger(__name__)
search_paths = contextvars.ContextVar("current search_paths in thread")
current_target = contextvars.ContextVar("current target in thread")


@cache
def inventory_global(lazy=False):
    # At hoc inventory for kadet
    if not cached.inventory_global_kadet:
        cached.inventory_global_kadet = Dict(cached.global_inv, default_box=lazy)
    return cached.inventory_global_kadet


def inventory(lazy=False):
    return inventory_global(lazy)[current_target.get()]


def inventory_frozen():
    return kadet.Box(data=inventory().dump(), frozen_box=True)


@cache
def inventory_digest(target_name):
    # XXX target_name parameter is only used for the LRU cache
    h = InputCache.hash_object()
    h.update(
        json.dumps(inventory_frozen(), sort_keys=True, default=str).encode("utf-8")
    )
    return h.digest()


def module_from_path(path, check_name=None):
    """
    loads python module in path
    set check_name to verify module name against spec name
    returns tuple with module and spec
    """

    if not os.path.isdir(path):
        raise FileNotFoundError(f"path: {path} must be an existing directory")

    module_name = os.path.basename(os.path.normpath(path))
    init_path = os.path.join(path, "__init__.py")
    spec = spec_from_file_location(f"kadet_component_{module_name}", init_path)
    mod = module_from_spec(spec)

    if spec is None:
        raise ModuleNotFoundError(f"Could not load module in path {path}")
    if check_name is not None and check_name != module_name:
        raise ModuleNotFoundError(
            f"Module name {module_name} does not match check_name {check_name}"
        )

    return mod, spec


def load_from_search_paths(module_name):
    """
    loads and executes python module with module_name from search paths
    returns module
    """
    for path in search_paths.get():
        try:
            _path = os.path.join(path, module_name)
            mod, spec = module_from_path(_path, check_name=module_name)
            spec.loader.exec_module(mod)
            return mod
        except (ModuleNotFoundError, FileNotFoundError):
            pass
    raise ModuleNotFoundError(f"Could not load module name {module_name}")


class Kadet(InputType):
    def compile_file(
        self, config: KapitanInputTypeKadetConfig, input_path, compile_path
    ):
        """
        Compile a kadet input file.

        Write the kadet evaluated items as files to compile_path.  External variables are not used in Kadet.
        """

        input_params = config.input_params
        target_name = self.target_name
        current_target.set(target_name)
        search_paths.set(self.search_paths)
        inputs_hash = None
        output_obj = None

        if cache_obj := self.cacheable():
            inputs_hash = self.inputs_hash(
                inventory_digest(current_target.get()),
                target_name,
                Path(input_path),
            )

            output_obj = cache_obj.get(inputs_hash)

        if output_obj is None:
            # set compile_path allowing kadet functions to have context on where files
            # are being compiled on the current kapitan run
            # we only do this if user didn't pass its own value
            input_params.setdefault("compile_path", compile_path)

            kadet_module, spec = module_from_path(input_path)
            sys.modules[spec.name] = kadet_module
            spec.loader.exec_module(kadet_module)
            logger.debug("Kadet.compile_file: spec.name: %s", spec.name)
            kadet_arg_spec = inspect.getfullargspec(kadet_module.main)
            logger.debug("Kadet main args: %s", kadet_arg_spec.args)

            if len(kadet_arg_spec.args) > 1:
                raise ValueError(
                    f"Kadet {spec.name} main parameters not equal to 1 or 0"
                )

            try:
                if len(kadet_arg_spec.args) == 1:
                    output_obj = kadet_module.main(input_params)
                elif len(kadet_arg_spec.args) == 0:
                    output_obj = kadet_module.main()

            except Exception as exc:
                raise CompileError(
                    f"Could not load Kadet module: {spec.name[16:]}"
                ) from exc

            output_obj = _to_dict(output_obj)

            if cache_obj := self.cacheable():
                cache_obj.set(inputs_hash, output_obj)

        # Return None if output_obj has no output
        if not output_obj:
            return

        for item_key, item_value in output_obj.items():
            file_path = os.path.join(compile_path, item_key)
            self.to_file(config, file_path, item_value)

    def inputs_hash(self, *inputs):
        """
        Calculates a deterministic hash for a variable set of inputs.

        This function return a consistent hash regardless of the
        order of the input arguments. It groups inputs by type (dict, list,
        str, int, bytes, Path), sorts them within their groups, and then
        calculates a final hash from the combined hashes of each group.

        - Dictionaries and lists are serialized to JSON with sorted keys.
        - Paths are recursively hashed using `walk_and_hash`.
        - All other types are converted to bytes and hashed.

        Args:
            *inputs: A variable number of inputs to be hashed.

        Returns:
            A hex digest string representing the deterministic hash of the inputs.
        """

        # Temporary lists for sortable representations of inputs
        dict_reps = []
        list_reps = []
        str_reps = []
        int_reps = []
        bytes_reps = []
        path_reps = []

        for i in inputs:
            if isinstance(i, dict):
                dict_reps.append(json.dumps(i, sort_keys=True, default=str))
            elif isinstance(i, list):
                list_reps.append(json.dumps(i, sort_keys=True, default=str))
            elif isinstance(i, str):
                str_reps.append(i)
            elif isinstance(i, int):
                int_reps.append(i)
            elif isinstance(i, bytes):
                bytes_reps.append(i)
            elif isinstance(i, Path):
                path_reps.append(i)

        # Sort the representations
        dict_reps.sort()
        list_reps.sort()
        str_reps.sort()
        int_reps.sort()
        bytes_reps.sort()
        path_reps.sort(key=str)  # Sort paths by their string representation

        # Hash the sorted representations
        h_dicts = InputCache.hash_object()
        for rep in dict_reps:
            h_dicts.update(rep.encode("utf-8"))

        h_lists = InputCache.hash_object()
        for rep in list_reps:
            h_lists.update(rep.encode("utf-8"))

        h_strs = InputCache.hash_object()
        for rep in str_reps:
            h_strs.update(rep.encode("utf-8"))

        h_ints = InputCache.hash_object()
        for rep in int_reps:
            h_ints.update(bytes(rep))

        h_bytes = InputCache.hash_object()
        for rep in bytes_reps:
            h_bytes.update(rep)

        h_paths = InputCache.hash_object()
        for rep in path_reps:
            walk_and_hash(rep, self.cacheable(), h_paths)

        h_final = InputCache.hash_object()
        h_final.update(
            h_dicts.digest()
            + h_lists.digest()
            + h_strs.digest()
            + h_ints.digest()
            + h_bytes.digest()
            + h_paths.digest()
        )

        return h_final.hexdigest()

    def cacheable(self):
        if cached.args.cache:
            if cached.kapitan_input_kadet is None:
                cached.kapitan_input_kadet = InputCache("kadet")

            return cached.kapitan_input_kadet
        return False


def walk_and_hash(path: Path, input_cache: InputCache, path_hash):
    """
    Recursively walk a path and update a hash object with the contents of all files.
    This implementation is deterministic.
    """
    if not path.exists() or str(path).endswith("__pycache__"):
        return

    if path.is_file():
        if cached_hash_digest := get_path_hash_from_input_kv(path, input_cache):
            path_hash.update(cached_hash_digest)
            logger.debug(
                "KV Memory hit for path: %s, digest: %s", path, path_hash.hexdigest()
            )
            return

        with open(path, "rb") as fp:
            file_hash = InputCache.hash_file_digest(fp)
            digest = file_hash.digest()
            set_path_hash_input_kv(path, digest, input_cache)
            path_hash.update(digest)

    elif path.is_dir():
        for item in sorted(path.iterdir(), key=lambda p: p.name):
            walk_and_hash(item, input_cache, path_hash)


def get_path_hash_from_input_kv(path: Path, input_cache: InputCache):
    try:
        # TODO temp hack to avoid input_cache being False
        if input_cache:
            return input_cache.kv_cache[str(path)]
    except KeyError:
        return None


def set_path_hash_input_kv(path: Path, h_file, input_cache: InputCache):
    # TODO temp hack to avoid input_cache being False
    if input_cache:
        input_cache.kv_cache[str(path)] = h_file


def _to_dict(obj):
    """
    recursively update obj should it contain other
    BaseObj values
    """
    if isinstance(obj, BaseObj | BaseModel):
        for k, v in obj.root.items():
            obj.root[k] = _to_dict(v)
        # BaseObj needs to return to_dict()
        return obj.root.to_dict()
    if isinstance(obj, list):
        obj = [_to_dict(item) for item in obj]
        # list has no .to_dict, return itself
        return obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _to_dict(v)
        # dict has no .to_dict, return itself
        return obj

    # anything else, return itself
    return obj
