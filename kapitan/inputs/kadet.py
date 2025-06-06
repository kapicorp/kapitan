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
from pathlib import Path, PurePath

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


@cache
def inventory_frozen():
    return kadet.Box(data=inventory().dump(), frozen_box=True)


@lru_cache(maxsize=None)
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

        kwargs:
            output (str): default 'yaml', accepts 'json', 'toml', 'plain'
            prune_output (bool): default False, prune empty dictionaries and lists from output
            reveal (bool): default False, set to True to reveal refs on compile
            target_name (str): default None, set to the current target being compiled
            indent (int): default 2, indentation level for yaml/json output
        """

        input_params = config.input_params
        target_name = self.target_name
        current_target.set(target_name)
        search_paths.set(self.search_paths)

        print("=config", config)
        print("=input_path", input_path)
        print("=target", current_target.get())

        hashed_inputs = self.inputs_hash(
            inventory_frozen(), input_params, Path(input_path)
        )
        print("=inputs_hash", hashed_inputs.hexdigest())

        cached_path = Path(PurePath("/tmp/", hashed_inputs.hexdigest()))
        print("=cached_path", cached_path)

        inputs_hash = None
        output_obj = None

        if cache_obj := self.cacheable():
            inputs_hash = self.inputs_hash(
                inventory_digest(target_name),
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

    def inputs_hash(self, *inputs, **kwargs):
        # Hash all inputs to kadet component.

        h_dicts = InputCache.hash_object()
        h_lists = InputCache.hash_object()
        h_strs = InputCache.hash_object()
        h_ints = InputCache.hash_object()
        h_bytes = InputCache.hash_object()
        h_paths = InputCache.hash_object()
        h_final = InputCache.hash_object()
        for i in inputs:
            if isinstance(i, dict):
                h_dicts.update(
                    json.dumps(i, sort_keys=True, default=str).encode("utf-8")
                )
            elif isinstance(i, list):
                h_lists.update(
                    json.dumps(i, sort_keys=True, default=str).encode("utf-8")
                )
            elif isinstance(i, str):
                h_strs.update(i.encode("utf-8"))
            elif isinstance(i, int):
                h_ints.update(bytes(i))
            elif isinstance(i, bytes):
                h_bytes.update(i)
            elif isinstance(i, Path):
                walk_and_hash(i, self.cacheable(), h_paths)

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
        else:
            return False


def walk_and_hash(path: Path, input_cache: InputCache, path_hash):
    # if path is in kv, use that instead
    if cached_hash_digest := get_path_hash_from_input_kv(path, input_cache):
        path_hash.update(cached_hash_digest)
        logger.debug(
            "KV Memory hit for path: %s, digest: %s", path, path_hash.hexdigest()
        )
        return

    if path.is_file():
        with open(path, "rb") as fp:
            file_hash = InputCache.hash_file_digest(fp)
            set_path_hash_input_kv(path, file_hash.digest(), input_cache)
            path_hash.update(file_hash.digest())

    if path.is_dir():
        for root, dirs, files in path.walk(follow_symlinks=True):
            # TODO there must be a better way to avoid pycache...
            if str(root).endswith("__pycache__"):
                continue
            for f in sorted(files):
                walk_and_hash(PurePath.joinpath(root, f), input_cache, path_hash)

        set_path_hash_input_kv(path, path_hash.digest(), input_cache)


def get_path_hash_from_input_kv(path: Path, input_cache: InputCache):
    try:
        return input_cache.kv_cache[str(path)]
    except KeyError:
        return None


def set_path_hash_input_kv(path: Path, h_file, input_cache: InputCache):
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
