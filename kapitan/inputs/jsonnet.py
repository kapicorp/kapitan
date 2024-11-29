#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os

from kapitan.errors import CompileError
from kapitan.inputs.base import CompiledFile, InputType
from kapitan.inventory.model.input_types import KapitanInputTypeJsonnetConfig
from kapitan.resources import resource_callbacks, search_imports
from kapitan.utils import prune_empty

logger = logging.getLogger(__name__)


def jsonnet_file(file_path, **kwargs):
    """Evaluates a Jsonnet file using the Python _jsonnet library.

    Args:
        file_path: Path to the Jsonnet file.
        **kwargs: Keyword arguments passed to the _jsonnet.evaluate_file function.
                  See http://jsonnet.org/implementation/bindings.html for details.

    Returns:
        str: The evaluated Jsonnet output as a string.

    Raises:
        ImportError: If the _jsonnet module is not installed.
        CompileError: If there is an error during Jsonnet evaluation.
    """
    try:
        import _jsonnet  # Import here to avoid dependency issues if Jsonnet is not used

        return _jsonnet.evaluate_file(file_path, **kwargs)
    except ImportError:
        raise ImportError(
            "Jsonnet is not installed or running on an unsupported architecture. "
            "See https://kapitan.dev/compile/#jsonnet for installation instructions."
        )
    except Exception as e:
        raise CompileError(f"Jsonnet error: failed to compile {file_path}:\n {e}") from e


def go_jsonnet_file(file_path, **kwargs):
    """Evaluates a Jsonnet file using the go-jsonnet library.

    Args:
        file_path: Path to the Jsonnet file.
        **kwargs: Keyword arguments passed to the _gojsonnet.evaluate_file function.
                  See http://jsonnet.org/implementation/bindings.html for details.

    Returns:
        str: The evaluated Jsonnet output as a string.

    Raises:
        ImportError: If the _gojsonnet module is not installed.
        CompileError: If there is an error during Jsonnet evaluation.

    """
    try:
        import _gojsonnet

        return _gojsonnet.evaluate_file(file_path, **kwargs)
    except ImportError:
        raise ImportError(
            "go-jsonnet is not installed or running on an unsupported architecture. "
            "See https://kapitan.dev/compile/#jsonnet for installation instructions."
        )

    except Exception as e:
        raise CompileError(f"Jsonnet error: failed to compile {file_path}:\n {e}") from e


class Jsonnet(InputType):
    """Jsonnet input type"""

    def __init__(self, config: KapitanInputTypeJsonnetConfig, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.use_go = self.args.use_go_jsonnet

    def compile_file(self, file_path, compile_path):
        """Compiles a Jsonnet file and writes the output to the compile directory.

        Args:
            file_path (str): Path to the Jsonnet file.
            compile_path (str): Path to the compile directory.

        Raises:
            CompileError: If there is an error compiling or writing the output.
            ValueError: If the specified output type is invalid.
        """

        ext_vars = {"target": self.target_name}

        def _search_imports(cwd, imp):
            return search_imports(cwd, imp, self.search_paths)

        try:
            if self.use_go:
                json_output = go_jsonnet_file(
                    file_path,
                    import_callback=_search_imports,
                    native_callbacks=resource_callbacks(self.search_paths),
                    ext_vars=ext_vars,
                )
            else:
                json_output = jsonnet_file(
                    file_path,
                    import_callback=_search_imports,
                    native_callbacks=resource_callbacks(self.search_paths),
                    ext_vars=ext_vars,
                )

            output_obj = json.loads(json_output)

        except (ImportError, CompileError) as e:
            raise CompileError(f"Jsonnet Error compiling {file_path}: {e}") from e

        output = self.config.output_type
        prune_output = self.config.prune
        reveal = self.args.reveal
        target_name = self.target_name
        indent = self.args.indent

        if prune_output:
            output_obj = prune_empty(output_obj)
            logger.debug("Pruned output for: %s", file_path)

        # If output_obj is not a dictionary, wrap it in a dictionary
        # using the input filename (without extension) as the key.
        if not isinstance(output_obj, dict):
            filename = os.path.splitext(os.path.basename(file_path))[0]
            output_obj = {filename: output_obj}

        # Write each item in output_obj to a separate file.
        for item_key, item_value in output_obj.items():
            file_ext = output
            if output in ["yml", "yaml"]:
                file_ext = "yaml"  # normalize extension
            elif output == "plain":
                file_ext = ""  # no extension for plain text

            file_name = f"{item_key}.{file_ext}" if file_ext else item_key
            file_path = os.path.join(compile_path, file_name)

            with CompiledFile(
                file_path,
                self.ref_controller,
                mode="w",
                reveal=reveal,
                target_name=target_name,
                indent=indent,
            ) as fp:
                if output == "json":
                    fp.write_json(item_value)
                elif output in ["yml", "yaml"]:
                    fp.write_yaml(item_value)
                elif output == "toml":
                    fp.write_toml(item_value)
                elif output == "plain":
                    fp.write(item_value)
                else:
                    raise ValueError(f"Invalid output type: {output}")
