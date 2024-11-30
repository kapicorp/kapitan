#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import abc
import glob
import itertools
import json
import logging
import os
from collections.abc import Mapping

import toml
import yaml

from kapitan import cached
from kapitan.errors import CompileError, KapitanError
from kapitan.inventory.model.input_types import CompileInputTypeConfig
from kapitan.refs.base import Revealer
from kapitan.utils import PrettyDumper

logger = logging.getLogger(__name__)


class InputType(object):
    """
    Abstract base class for input types.

    Provides methods for compiling input files.  Subclasses should implement
    the `compile_file` method to handle specific input formats.

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, compile_path, search_paths, ref_controller, target_name, args):
        self.compile_path = compile_path
        self.search_paths = search_paths
        self.ref_controller = ref_controller
        self.target_name = target_name
        self.args = args

    def compile_obj(self, comp_obj: CompileInputTypeConfig):
        """Expand globbed input paths and compile each resolved input path.

        Args:
            comp_obj: CompileInputTypeConfig object containing input paths and other compilation options.

        Raises:
            CompileError: If an input path is not found and ignore_missing is False.

        """

        # expand any globbed paths, taking into account provided search paths
        expanded_input_paths = []
        for input_path in comp_obj.input_paths:
            globbed_paths = [glob.glob(os.path.join(path, input_path)) for path in self.search_paths]
            inputs = list(itertools.chain.from_iterable(globbed_paths))
            # remove duplicate inputs
            inputs = set(inputs)
            ignore_missing = comp_obj.ignore_missing
            if len(inputs) == 0 and not ignore_missing:
                raise CompileError(
                    "Compile error: {} for target: {} not found in "
                    "search_paths: {}".format(input_path, self.target_name, self.search_paths)
                )
            expanded_input_paths.extend(inputs)

        for expanded_path in expanded_input_paths:
            self.compile_input_path(comp_obj, expanded_path)

    def compile_input_path(self, comp_obj: CompileInputTypeConfig, input_path: str):
        """Compile a single input path.

        Args:
            comp_obj: CompileInputTypeConfig object.
            input_path: Path to the input file.

        Raises:
            CompileError: If compilation fails.

        """
        target_name = self.target_name
        output_path = comp_obj.output_path

        logger.debug("Compiling %s", input_path)
        try:
            target_compile_path = os.path.join(self.compile_path, target_name.replace(".", "/"), output_path)
            os.makedirs(target_compile_path, exist_ok=True)

            self.compile_file(
                comp_obj,
                input_path,
                target_compile_path,
            )

        except KapitanError as e:
            raise CompileError("{}\nCompile error: failed to compile target: {}".format(e, target_name))

    @abc.abstractmethod
    def compile_file(self, config: CompileInputTypeConfig, input_path: str, compile_path: str):
        """Compile a single input file.

        Args:
            config: CompileInputTypeConfig object.
            input_path: Path to the input file.
            compile_path: Path to the output directory.

        Raises:
            NotImplementedError: This is an abstract method.

        """
        return NotImplementedError


class CompilingFile(object):
    def __init__(self, context, fp, ref_controller, **kwargs):
        self.fp = fp
        self.ref_controller = ref_controller
        self.kwargs = kwargs
        self.revealer = Revealer(ref_controller)

    def write(self, data):
        """write data into file"""
        reveal = self.kwargs.get("reveal", False)
        target_name = self.kwargs.get("target_name", None)

        if reveal:
            self.fp.write(self.revealer.reveal_raw(data))
        else:
            self.fp.write(self.revealer.compile_raw(data, target_name=target_name))

    def write_yaml(self, obj):
        """recursively compile or reveal refs and convert obj to yaml and write to file"""
        indent = self.kwargs.get("indent", 2)
        reveal = self.kwargs.get("reveal", False)
        target_name = self.kwargs.get("target_name", None)

        # TODO(ademaria): make it configurable per input type
        style_selection = cached.inv[target_name]["parameters"].get("multiline_string_style", None)

        if not style_selection:
            if hasattr(cached.args, "multiline_string_style"):
                style_selection = cached.args.multiline_string_style
            elif hasattr(cached.args, "yaml_multiline_string_style"):
                style_selection = cached.args.yaml_multiline_string_style

        dumper = PrettyDumper.get_dumper_for_style(style_selection)

        if reveal:
            obj = self.revealer.reveal_obj(obj)
        else:
            obj = self.revealer.compile_obj(obj, target_name=target_name)

        if obj:
            if isinstance(obj, Mapping):
                yaml.dump(
                    obj,
                    stream=self.fp,
                    indent=indent,
                    Dumper=dumper,
                    default_flow_style=False,
                )
            else:
                yaml.dump_all(
                    obj,
                    stream=self.fp,
                    indent=indent,
                    Dumper=dumper,
                    default_flow_style=False,
                )

            logger.debug("Wrote %s", self.fp.name)
        else:
            logger.debug("%s is Empty, skipped writing output", self.fp.name)

    def write_json(self, obj):
        """recursively hash or reveal refs and convert obj to json and write to file"""
        indent = self.kwargs.get("indent", 2)
        reveal = self.kwargs.get("reveal", False)
        target_name = self.kwargs.get("target_name", None)
        if reveal:
            obj = self.revealer.reveal_obj(obj)
        else:
            obj = self.revealer.compile_obj(obj, target_name=target_name)
        if obj:
            json.dump(obj, self.fp, indent=indent)
            logger.debug("Wrote %s", self.fp.name)
        else:
            logger.debug("%s is Empty, skipped writing output", self.fp.name)

    def write_toml(self, obj):
        """recursively compile or reveal refs and convert obj to toml and write to file"""
        reveal = self.kwargs.get("reveal", False)
        target_name = self.kwargs.get("target_name", None)
        if reveal:
            obj = self.revealer.reveal_obj(obj)
        else:
            obj = self.revealer.compile_obj(obj, target_name=target_name)
        if obj:
            toml.dump(obj, self.fp)
            logger.debug("Wrote %s", self.fp.name)
        else:
            logger.debug("%s is Empty, skipped writing output", self.fp.name)


class CompiledFile(object):
    def __init__(self, name, ref_controller, **kwargs):
        self.name = name
        self.fp = None
        self.ref_controller = ref_controller
        self.kwargs = kwargs

    def __enter__(self):
        mode = self.kwargs.get("mode", "r")

        # make sure directory for file exists
        os.makedirs(os.path.dirname(self.name), exist_ok=True)

        self.fp = open(self.name, mode)
        return CompilingFile(self, self.fp, self.ref_controller, **self.kwargs)

    def __exit__(self, *args):
        self.fp.close()
