#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location

import yaml
from addict import Dict
from kapitan.errors import CompileError
from kapitan.inputs.base import CompiledFile, InputType
from kapitan.resources import inventory as inventory_func
from kapitan.utils import prune_empty

logger = logging.getLogger(__name__)
inventory = None
inventory_global = None
search_paths = None


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
    for path in search_paths:
        try:
            _path = os.path.join(path, module_name)
            mod, spec = module_from_path(_path, check_name=module_name)
            spec.loader.exec_module(mod)
            return mod
        except (ModuleNotFoundError, FileNotFoundError):
            pass
    raise ModuleNotFoundError("Could not load module name {}".format(module_name))


class Kadet(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("kadet", compile_path, search_paths, ref_controller)

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
        indent = kwargs.get("indent", 2)

        # These will be updated per target
        # XXX At the moment we have no other way of setting externals for modules...
        global search_paths
        search_paths = self.search_paths
        global inventory
        inventory = lambda: Dict(inventory_func(self.search_paths, target_name))  # noqa E731
        global inventory_global
        inventory_global = lambda: Dict(inventory_func(self.search_paths, None))  # noqa E731

        kadet_module, spec = module_from_path(file_path)
        sys.modules[spec.name] = kadet_module
        spec.loader.exec_module(kadet_module)
        logger.debug("Kadet.compile_file: spec.name: %s", spec.name)

        output_obj = kadet_module.main().to_dict()
        if prune:
            output_obj = prune_empty(output_obj)

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
            elif output == "yaml":
                file_path = os.path.join(compile_path, "%s.%s" % (item_key, "yml"))
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
            else:
                raise ValueError(
                    f"Output type defined in inventory for {file_path} is neither 'json', 'yaml' nor 'plain'"
                )
            logger.debug("Pruned output for: %s", file_path)

    def default_output_type(self):
        return "yaml"


class BaseObj(object):
    def __init__(self, **kwargs):
        """
        returns a BaseObj
        kwargs will be save into self.kwargs
        values in self.root are returned as dict via self.to_dict()
        """
        self.root = Dict()
        self.kwargs = Dict(kwargs)
        self.new()
        self.body()

    @classmethod
    def from_json(cls, file_path):
        """
        returns a BaseObj initialised with json content
        from file_path
        """
        with open(file_path) as fp:
            json_obj = json.load(fp)
            return cls.from_dict(json_obj)

    @classmethod
    def from_yaml(cls, file_path):
        """
        returns a BaseObj initialised with yaml content
        from file_path
        """
        with open(file_path) as fp:
            yaml_obj = yaml.safe_load(fp)
            return cls.from_dict(yaml_obj)

    @classmethod
    def from_dict(cls, dict_value):
        """
        returns a BaseObj initialise with dict_value
        """
        bobj = cls()
        bobj.root = Dict(dict_value)
        return bobj

    def update_root(self, file_path):
        """
        update self.root with YAML/JSON content in file_path
        raises CompileError if file_path does not end with .yaml, .yml or .json
        """
        with open(file_path) as fp:
            if file_path.endswith(".yaml") or file_path.endswith(".yml"):
                yaml_obj = yaml.safe_load(fp)
                _copy = dict(self.root)
                _copy.update(yaml_obj)
                self.root = Dict(_copy)

            elif file_path.endswith(".json"):
                json_obj = json.load(fp)
                _copy = dict(self.root)
                _copy.update(json_obj)
                self.root = Dict(_copy)
            else:
                raise CompileError("file_path is neither JSON or YAML: {}".format(file_path))

    def need(self, key, msg="key and value needed"):
        """
        requires that key is set in self.kwargs
        errors with msg if key not set
        """
        err_msg = '{}: "{}": {}'.format(self.__class__.__name__, key, msg)
        if key not in self.kwargs:
            raise CompileError(err_msg)

    def new(self):
        """
        initialise need()ed keys for
        a new BaseObj
        """
        pass

    def body(self):
        """
        set values/logic for self.root
        """
        pass

    def _to_dict(self, obj):
        """
        recursively update obj should it contain other
        BaseObj values
        """
        if isinstance(obj, BaseObj):
            for k, v in obj.root.items():
                obj.root[k] = self._to_dict(v)
            # BaseObj needs to return to_dict()
            return obj.root.to_dict()
        elif isinstance(obj, list):
            obj = [self._to_dict(item) for item in obj]
            # list has no .to_dict, return itself
            return obj
        elif isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self._to_dict(v)
            # dict has no .to_dict, return itself
            return obj

        # anything else, return itself
        return obj

    def to_dict(self):
        """
        returns object dict
        """
        return self._to_dict(self)
