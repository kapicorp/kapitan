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
from kapitan.inventory.model.input_types import CompileInputTypeConfig, OutputType
from kapitan.refs.base import Revealer
from kapitan.utils import PrettyDumper, prune_empty

logger = logging.getLogger(__name__)


class InputType(object):
    """
    Abstract base class for input types.

    Provides methods for compiling input files.  Subclasses should implement
    the `compile_file` method to handle specific input formats.

    """

    __metaclass__ = abc.ABCMeta
    output_type_default = OutputType.YAML

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

    def to_file(self, config: CompileInputTypeConfig, file_path, file_content):
        """Write compiled content to file, handling different output types and revealing refs if needed.

        Args:
            config: CompileInputTypeConfig object.
            file_path: Path to the output file.
            file_content: Compiled content to write.

        Raises:
            ValueError: If the output type is not supported.
        """
        reveal = self.args.reveal
        target_name = self.target_name

        indent = self.args.indent
        output_type = config.output_type
        file_ext = output_type

        if config.prune:
            file_content = prune_empty(file_content)

        if output_type == OutputType.AUTO:
            _, detected_type = os.path.splitext(file_path)
            if detected_type:
                # Remove . from the beginning of the extension
                detected_type = detected_type[1:]

            if detected_type in [OutputType.TOML, OutputType.JSON, OutputType.YAML, OutputType.YML]:
                output_type = detected_type
                file_ext = None
            else:
                # Extension is not handled, falling back to input type default
                output_type = self.output_type_default
                logger.debug("Could not detect extension for %s, defaulting to %s", file_path, output_type)
                file_ext = output_type  # no extension for plain text

        if output_type == OutputType.PLAIN:
            file_ext = None  # no extension for plain text

        file_name = f"{file_path}.{file_ext}" if file_ext else file_path

        with CompiledFile(
            # file_path: path to the output file
            file_name,
            # ref_controller: reference controller to resolve refs
            self.ref_controller,
            # mode: file open mode, 'w' for write
            mode="w",
            # reveal: reveal refs in output
            reveal=reveal,
            target_name=target_name,
            indent=indent,
        ) as fp:
            if output_type == OutputType.JSON:
                fp.write_json(file_content)
            elif output_type in [OutputType.YAML, OutputType.YML]:
                fp.write_yaml(file_content)
            elif output_type == OutputType.PLAIN:
                fp.write(file_content)
            elif output_type == OutputType.TOML:
                fp.write_toml(file_content)
            else:
                raise ValueError(
                    f"Output type defined in inventory for {config} not supported: {output_type}: {OutputType}"
                )

    def compile_input_path(self, comp_obj: CompileInputTypeConfig, input_path: str):
        """Compile a single input path and write the result to the output directory.

        Creates the output directory if it doesn't exist.

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
            raise CompileError(
                "{}\nCompile error: failed to compile target: {}".format(e, target_name)
            ) from e

    @abc.abstractmethod
    def compile_file(self, config: CompileInputTypeConfig, input_path: str, compile_path: str):
        """Compile a single input file.

        This is an abstract method that should be implemented by subclasses to handle
        specific input formats.

        Args:
            config: CompileInputTypeConfig object.
            input_path: Path to the input file.
            compile_path: Path to the output directory.
        """
        return NotImplementedError


class CompilingFile(object):
    """
    A class to handle writing compiled data to a file.

    Provides methods to write data in different formats (YAML, JSON, TOML) to a file,
    handling reference revealing and compilation as needed.

    Args:
        fp: File object to write to.
        ref_controller: Reference controller to resolve references.
        **kwargs: Additional keyword arguments (e.g., reveal, target_name, indent).
    """

    def __init__(self, fp, ref_controller, **kwargs):
        self.fp = fp
        self.kwargs = kwargs
        self.revealer = Revealer(ref_controller)

    def write(self, data):
        """Write data into file.

        Args:
            data: Data to write.

        Reveals references if `reveal` is True in kwargs.

        """
        reveal = self.kwargs.get("reveal", False)
        target_name = self.kwargs.get("target_name", None)

        if reveal:
            self.fp.write(self.revealer.reveal_raw(data))
        else:
            self.fp.write(self.revealer.compile_raw(data, target_name=target_name))

    def write_yaml(self, obj: object):
        """Recursively compile or reveal refs and convert obj to YAML and write to file.

        Args:
            obj: Object to write.

        Uses PrettyDumper to handle multiline strings according to style selection.
        """
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

    def write_json(self, obj: object):
        """Recursively compile or reveal refs and convert obj to JSON and write to file.

        Args:
            obj: Object to write.

        Reveals references if `reveal` is True in kwargs.
        """
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

    def write_toml(self, obj: object):
        """Recursively compile or reveal refs and convert obj to TOML and write to file.

        Args:
            obj: Object to write.

        Reveals references if `reveal` is True in kwargs.
        """
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
    """
    A context manager to handle writing compiled data to a file.

    Args:
        name: Name of the output file.
        ref_controller: Reference controller to resolve references.
        **kwargs: Additional keyword arguments (e.g., mode).

    """

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
        return CompilingFile(self.fp, self.ref_controller, **self.kwargs)

    def __exit__(self, *args):
        self.fp.close()
