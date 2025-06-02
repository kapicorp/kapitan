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
from functools import lru_cache
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


@lru_cache(maxsize=None)
def inventory_global(lazy=False):
    # At hoc inventory for kadet
    if not cached.inventory_global_kadet:
        cached.inventory_global_kadet = Dict(cached.global_inv, default_box=lazy)
    return cached.inventory_global_kadet


def inventory(lazy=False):
    return inventory_global(lazy)[current_target.get()]


@lru_cache(maxsize=None)
def inventory_frozen():
    return kadet.Box(data=inventory().dump(), frozen_box=True)


def module_from_path(path, check_name=None):
    """
    loads python module in path
    set check_name to verify module name against spec name
    returns tuple with module and spec
    """

    if not os.path.isdir(path):
        raise FileNotFoundError("path: {} must be an existing directory".format(path))

    module_name = os.path.basename(os.path.normpath(path))
    init_path = os.path.join(path, "__init__.py")
    spec = spec_from_file_location("kadet_component_{}".format(module_name), init_path)
    mod = module_from_spec(spec)

    if spec is None:
        raise ModuleNotFoundError("Could not load module in path {}".format(path))
    if check_name is not None and check_name != module_name:
        raise ModuleNotFoundError(
            "Module name {} does not match check_name {}".format(module_name, check_name)
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
    raise ModuleNotFoundError("Could not load module name {}".format(module_name))


class Kadet(InputType):
    def compile_file(self, config: KapitanInputTypeKadetConfig, input_path, compile_path):
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
        output_obj = None

        if cache_obj := self.cacheable():
            inputs_hash = self.inputs_hash(inventory_frozen(), input_params, Path(input_path))
            output_obj = cache_obj.get(inputs_hash)
        # else, compile
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
                raise ValueError(f"Kadet {spec.name} main parameters not equal to 1 or 0")

            try:
                if len(kadet_arg_spec.args) == 1:
                    output_obj = kadet_module.main(input_params)
                elif len(kadet_arg_spec.args) == 0:
                    output_obj = kadet_module.main()

            except Exception as exc:
                raise CompileError(f"Could not load Kadet module: {spec.name[16:]}") from exc

            output_obj = _to_dict(output_obj)

            if cache_obj := self.cacheable():
                cache_obj.set(inputs_hash, output_obj)

        # Return None if output_obj has no output
        if not output_obj:
            return None

        for item_key, item_value in output_obj.items():
            file_path = os.path.join(compile_path, item_key)
            self.to_file(config, file_path, item_value)

    def inputs_hash(self, *inputs, **kwargs):
        # Hash all inputs to kadet component.
        # Can we hash refs? Or do we need to hash all refs? Or do can we infer ref as dependencies?

        # this should be hidden away in a subsystem to ensure hash function is standard accross inputs
        h = InputCache.hash_object()
        for i in inputs:
            if isinstance(i, (dict, list)):
                h.update(json.dumps(i, sort_keys=True).encode("utf-8"))
            if isinstance(i, str):
                h.update(i)
            if isinstance(i, int):
                h.update(bytes(int))
            if isinstance(i, Path):
                # walk and update hash
                def walk_and_hash(path: Path):
                    if path.is_file():
                        h.update(open(path, "rb").read())

                    if path.is_dir():
                        for root, dirs, files in path.walk(follow_symlinks=True):
                            for f in files:
                                # TODO there must be a better way to avoid pycache...
                                if not str(root).endswith("__pycache__"):
                                    walk_and_hash(PurePath.joinpath(root, f))

                walk_and_hash(i)
        return h.hexdigest()

    def cacheable(self):
        if cached.args.cache:
            self.cache = InputCache("kadet")
            return self.cache
        else:
            return None


def _to_dict(obj):
    """
    recursively update obj should it contain other
    BaseObj values
    """
    if isinstance(obj, (BaseObj, BaseModel)):
        for k, v in obj.root.items():
            obj.root[k] = _to_dict(v)
        # BaseObj needs to return to_dict()
        return obj.root.to_dict()
    elif isinstance(obj, list):
        obj = [_to_dict(item) for item in obj]
        # list has no .to_dict, return itself
        return obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _to_dict(v)
        # dict has no .to_dict, return itself
        return obj

    # anything else, return itself
    return obj
