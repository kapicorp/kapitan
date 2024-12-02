#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os

from kapitan.errors import CompileError
from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import KapitanInputTypeJsonnetConfig
from kapitan.resources import resource_callbacks, search_imports

logger = logging.getLogger(__name__)


def select_jsonnet_runtime(use_go):
    """Selects the Jsonnet runtime to use.

    Args:
        use_go: Boolean indicating whether to use the Go Jsonnet runtime.

    Returns:
        module: The selected Jsonnet runtime module (_jsonnet or _gojsonnet).

    Raises:
        ImportError: If the selected Jsonnet runtime is not installed.  This will happen if neither
                     the python or go jsonnet libraries are installed.  The error message will
                     provide instructions on how to install the necessary library.
    Raises:
        ImportError: If the _jsonnet module is not installed.
        CompileError: If there is an error during Jsonnet evaluation.
    """
    try:
        if use_go:
            import _gojsonnet

            return _gojsonnet
        else:
            import _jsonnet

            return _jsonnet

    except ImportError as exc:
        raise ImportError(
            "Jsonnet is not installed or running on an unsupported architecture. "
            "See https://kapitan.dev/compile/#jsonnet for installation instructions."
        ) from exc


class Jsonnet(InputType):
    """Jsonnet input type."""

    def compile_file(self, config: KapitanInputTypeJsonnetConfig, input_path: str, compile_path: str):
        """Compiles a Jsonnet file and writes the output to the compile directory.

        Args:
            config: KapitanInputTypeJsonnetConfig object containing compilation options.
            input_path: Path to the Jsonnet file to compile.
            compile_path: Path to the directory where compiled output will be written.

        Raises:
            CompileError: If there is an error compiling or writing the output.
            ValueError: If the specified output type is invalid.

        This function evaluates the Jsonnet file, handles different output formats (json, yaml, toml, plain),
        prunes empty values if requested, and writes the results to individual files in the
        compile directory.
        """

        use_go = self.args.use_go_jsonnet
        ext_vars = {"target": self.target_name}

        def _search_imports(cwd, imp):
            return search_imports(cwd, imp, self.search_paths)

        try:
            jsonnet = select_jsonnet_runtime(use_go)
            json_output = jsonnet.evaluate_file(
                input_path,
                import_callback=_search_imports,
                native_callbacks=resource_callbacks(self.search_paths),
                ext_vars=ext_vars,
            )

            output_obj = json.loads(json_output)

        except (ImportError, CompileError) as e:
            raise CompileError(f"Jsonnet Error compiling {input_path}: {e}") from e

        # If output_obj is not a dictionary, wrap it in a dictionary using the input filename
        # (without extension) as the key. This ensures that even single-item outputs are handled correctly.
        if not isinstance(output_obj, dict):
            filename = os.path.splitext(os.path.basename(input_path))[0]
            # Using filename as key ensures that single-item outputs are handled correctly.
            # Prevents issues when a single item is returned and needs to be written to a file.
            output_obj = {filename: output_obj}

        # Write each item in output_obj to a separate file.
        for item_key, item_value in output_obj.items():
            file_path = os.path.join(compile_path, item_key)
            self.to_file(config, file_path, item_value)
