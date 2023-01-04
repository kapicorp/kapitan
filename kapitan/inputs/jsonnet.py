#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import sys

from kapitan.errors import CompileError
from kapitan.inputs.base import CompiledFile, InputType
from kapitan.resources import resource_callbacks, search_imports
from kapitan.utils import prune_empty

logger = logging.getLogger(__name__)


def jsonnet_file(file_path, **kwargs):
    """
    Evaluate file_path jsonnet file.
    kwargs are documented in http://jsonnet.org/implementation/bindings.html
    """
    try:
        if "_jsonnet" not in sys.modules:
            import _jsonnet
        return sys.modules["_jsonnet"].evaluate_file(file_path, **kwargs)
    except ImportError:
        logger.info(
            "Note: Jsonnet is not installed or running on an unsupported architecture."
            " See https://kapitan.dev/compile/#jsonnet"
        )
    except Exception as e:
        raise CompileError(f"Jsonnet error: failed to compile {file_path}:\n {e}")


def go_jsonnet_file(file_path, **kwargs):
    """
    Evaluate file_path jsonnet file using gojsonnet.
    kwargs are documented in http://jsonnet.org/implementation/bindings.html
    """
    try:
        if "_gojsonnet" not in sys.modules:
            import _gojsonnet
        return sys.modules["_gojsonnet"].evaluate_file(file_path, **kwargs)
    except ImportError:
        logger.info(
            "Note: Go-jsonnet is not installed or running on an unsupported architecture."
            " See https://kapitan.dev/compile/#jsonnet"
        )
    except Exception as e:
        raise CompileError(f"Jsonnet error: failed to compile {file_path}:\n {e}")


class Jsonnet(InputType):
    def __init__(self, compile_path, search_paths, ref_controller, use_go=False):
        super().__init__(
            "jsonnet",
            compile_path,
            search_paths,
            ref_controller,
        )
        self.use_go = use_go

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write file_path (jsonnet evaluated) items as files to compile_path.
        ext_vars will be passed as parameters to jsonnet_file()
        kwargs:
            output: default 'yaml', accepts 'json'
            prune: default False, accepts True
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled
            indent: default 2
        """

        def _search_imports(cwd, imp):
            return search_imports(cwd, imp, self.search_paths)

        json_output = None
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

        output = kwargs.get("output", "yaml")
        prune = kwargs.get("prune_input", False)
        reveal = kwargs.get("reveal", False)
        target_name = kwargs.get("target_name", None)
        indent = kwargs.get("indent", 2)

        if prune:
            output_obj = prune_empty(output_obj)
            logger.debug("Pruned output for: %s", file_path)

        if not isinstance(output_obj, dict):
            tmp_output_obj = output_obj
            # assume that the output filename is the
            # same as the input jsonnet filename
            filename = os.path.splitext(os.path.basename(file_path))[0]
            output_obj = {}
            output_obj[filename] = tmp_output_obj

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
