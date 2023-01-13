#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextvars
import inspect
import logging
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location

import kadet
from kadet import BaseModel, BaseObj, Dict

from kapitan import cached
from kapitan.errors import CompileError
from kapitan.inputs.base import CompiledFile, InputType
from kapitan.resources import inventory as inventory_func
from kapitan.utils import prune_empty

# Set external kadet exception to kapitan.error.CompileError
kadet.ABORT_EXCEPTION_TYPE = CompileError

logger = logging.getLogger(__name__)
inventory_path = cached.args.get(
    "inventory_path"
)  # XXX think about this as it probably breaks usage as library
search_paths = contextvars.ContextVar("current search_paths in thread")
current_target = contextvars.ContextVar("current target in thread")


def inventory(lazy=False):
    return Dict(inventory_func(search_paths.get(), current_target.get(), inventory_path), default_box=lazy)


def inventory_global(lazy=False):
    return Dict(inventory_func(search_paths.get(), None, inventory_path), default_box=lazy)


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
    def __init__(self, compile_path, search_paths, ref_controller, input_params={}):
        super().__init__("kadet", compile_path, search_paths, ref_controller)
        self.input_params = input_params

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write file_path (kadet evaluated) items as files to compile_path.
        ext_vars is not used in Kadet
        kwargs:
            output: default 'yaml', accepts 'json'
            prune: default False
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled
            indent: default 2
        """
        output = kwargs.get("output", "yaml")
        prune = kwargs.get("prune", False)
        reveal = kwargs.get("reveal", False)
        target_name = kwargs.get("target_name", None)
        # inventory_path = kwargs.get("inventory_path", None)
        indent = kwargs.get("indent", 2)

        current_target.set(target_name)
        search_paths.set(self.search_paths)

        input_params = self.input_params
        # set compile_path allowing kadet functions to have context on where files
        # are being compiled on the current kapitan run
        # we only do this if user didn't pass its own value
        input_params.setdefault("compile_path", compile_path)

        kadet_module, spec = module_from_path(file_path)
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
        except Exception:
            # Log traceback and exception as is
            logger.exception("")
            raise CompileError(f"Could not load Kadet module: {spec.name[16:]}")

        output_obj = _to_dict(output_obj)
        if prune:
            output_obj = prune_empty(output_obj)

        # Return None if output_obj has no output
        if not output_obj:
            return None

        for item_key, item_value in output_obj.items():
            # write each item to disk
            if output == "json":
                file_path = os.path.join(compile_path, "%s.%s" % (item_key, output))
                with CompiledFile(
                    file_path,
                    self.ref_controller,
                    mode="w",
                    reveal=reveal,
                    target_name=target_name,
                    indent=indent,
                ) as fp:
                    fp.write_json(item_value)
            elif output in ["yml", "yaml"]:
                file_path = os.path.join(compile_path, "%s.%s" % (item_key, output))
                with CompiledFile(
                    file_path,
                    self.ref_controller,
                    mode="w",
                    reveal=reveal,
                    target_name=target_name,
                    indent=indent,
                ) as fp:
                    fp.write_yaml(item_value)
            elif output == "plain":
                file_path = os.path.join(compile_path, "%s" % item_key)
                with CompiledFile(
                    file_path,
                    self.ref_controller,
                    mode="w",
                    reveal=reveal,
                    target_name=target_name,
                    indent=indent,
                ) as fp:
                    fp.write(item_value)
            elif output == "toml":
                file_path = os.path.join(compile_path, "%s.%s" % (item_key, output))
                with CompiledFile(
                    file_path,
                    self.ref_controller,
                    mode="w",
                    reveal=reveal,
                    target_name=target_name,
                    indent=indent,
                ) as fp:
                    fp.write_toml(item_value)
            else:
                raise ValueError(
                    f"Output type defined in inventory for {file_path} is neither 'json', 'yaml', 'toml' nor 'plain'"
                )

    def default_output_type(self):
        return "yaml"


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
