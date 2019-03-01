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

import logging
import os
import yaml
import json

from kapitan.errors import CompileError, KapitanError
from kapitan.refs.base import Revealer
from kapitan.utils import PrettyDumper

logger = logging.getLogger(__name__)


class InputType(object):
    def __init__(self, type_name, compile_path, search_paths, ref_controller):
        self.type_name = type_name
        self.compile_path = compile_path
        self.search_paths = search_paths
        self.ref_controller = ref_controller

    def compile_obj(self, comp_obj, ext_vars, **kwargs):
        """
        run compile_input_path() for each input_path in comp_obj
        kwargss are passed into compile_input_path()
        """
        input_type = comp_obj["input_type"]
        assert input_type == self.type_name
        input_paths = comp_obj["input_paths"]

        for input_path in input_paths:
            self.compile_input_path(input_path, comp_obj, ext_vars, **kwargs)

    def compile_input_path(self, input_path, comp_obj, ext_vars, **kwargs):
        """
        compile and validate input_path in comp_obj
        kwargs are passed into compile_file()
        """
        target_name = ext_vars["target"]
        output_path = comp_obj["output_path"]
        output_type = comp_obj.get("output_type", self.default_output_type())
        file_found = False

        for path in self.search_paths:
            compile_file_sp = os.path.join(path, input_path)
            if os.path.exists(compile_file_sp):
                file_found = True
                logger.debug("Compiling %s", compile_file_sp)
                try:
                    _compile_path = os.path.join(self.compile_path, target_name, output_path)
                    self.compile_file(compile_file_sp, _compile_path, ext_vars, output=output_type,
                                      target_name=target_name, **kwargs)
                except KapitanError as e:
                    raise CompileError("{}\nCompile error: failed to compile target: {}".format(e, target_name))

        if not file_found:
            raise CompileError("Compile error: {} for target: {} not found in "
                               "search_paths: {}".format(input_path, target_name, self.search_paths))

    def make_compile_dirs(self, target_name, output_path):
        """make compile dirs, skips if dirs exist"""
        _compile_path = os.path.join(self.compile_path, target_name, output_path)
        # support writing to an already existent dir
        os.makedirs(_compile_path, exist_ok=True)

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """implements compilation for file_path to compile_path with ext_vars"""
        return NotImplementedError

    def default_output_type(self):
        "returns default output_type value"
        return NotImplementedError


class CompilingFile(object):
    def __init__(self, context, fp, ref_controller, **kwargs):
        self.fp = fp
        self.ref_controller = ref_controller
        self.kwargs = kwargs
        self.revealer = Revealer(ref_controller)

    def write(self, data):
        """write data into file"""
        reveal = self.kwargs.get('reveal', False)
        target_name = self.kwargs.get('target_name', None)
        if reveal:
            self.fp.write(self.revealer.reveal_raw(data))
        else:
            self.fp.write(self.revealer.compile_raw(data, target_name=target_name))

    def write_yaml(self, obj):
        """recursively compile or reveal refs and convert obj to yaml and write to file"""
        indent = self.kwargs.get('indent', 2)
        reveal = self.kwargs.get('reveal', False)
        target_name = self.kwargs.get('target_name', None)
        if reveal:
            self.revealer.reveal_obj(obj)
        else:
            self.revealer.compile_obj(obj, target_name=target_name)
        yaml.dump(obj, stream=self.fp, indent=indent, Dumper=PrettyDumper, default_flow_style=False)
        logger.debug("Wrote %s", self.fp.name)

    def write_json(self, obj):
        """recursively hash or reveal refs and convert obj to json and write to file"""
        indent = self.kwargs.get('indent', 2)
        reveal = self.kwargs.get('reveal', False)
        target_name = self.kwargs.get('target_name', None)
        if reveal:
            self.revealer.reveal_obj(obj)
        else:
            self.revealer.compile_obj(obj, target_name=target_name)
        json.dump(obj, self.fp, indent=indent)
        logger.debug("Wrote %s", self.fp.name)


class CompiledFile(object):
    def __init__(self, name, ref_controller, **kwargs):
        self.name = name
        self.fp = None
        self.ref_controller = ref_controller
        self.kwargs = kwargs

    def __enter__(self):
        mode = self.kwargs.get("mode", "r")
        self.fp = open(self.name, mode)
        return CompilingFile(self, self.fp, self.ref_controller, **self.kwargs)

    def __exit__(self, *args):
        self.fp.close()
