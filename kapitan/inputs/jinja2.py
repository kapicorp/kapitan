#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os

from kapitan.inputs.base import CompiledFile, InputType
from kapitan.resources import inventory
from kapitan.utils import render_jinja2

logger = logging.getLogger(__name__)


class Jinja2(InputType):
    def __init__(self, compile_path, search_paths, ref_controller, args):
        super().__init__("jinja2", compile_path, search_paths, ref_controller)
        self.strip_postfix = args.get("suffix_remove", False)
        self.stripped_postfix = args.get("suffix_stripped", ".j2")
        self.input_params = args.get("input_params", {})

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write items in path as jinja2 rendered files to compile_path.
        path can be either a file or directory.
        kwargs:
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled
        """
        reveal = kwargs.get("reveal", False)
        target_name = kwargs.get("target_name", None)

        input_params = self.input_params
        # set compile_path allowing jsonnet to have context on where files
        # are being compiled on the current kapitan run
        # we only do this if user didn't pass its own value
        input_params.setdefault("compile_path", compile_path)

        # set ext_vars and inventory for jinja2 context
        context = ext_vars.copy()
        context["inventory"] = inventory(self.search_paths, target_name)
        context["inventory_global"] = inventory(self.search_paths, None)
        context["input_params"] = input_params

        jinja2_filters = kwargs.get("jinja2_filters")

        for item_key, item_value in render_jinja2(
            file_path, context, jinja2_filters=jinja2_filters, search_paths=self.search_paths
        ).items():
            if self.strip_postfix and item_key.endswith(self.stripped_postfix):
                item_key = item_key.rstrip(self.stripped_postfix)
            full_item_path = os.path.join(compile_path, item_key)
            with CompiledFile(
                full_item_path, self.ref_controller, mode="w", reveal=reveal, target_name=target_name
            ) as fp:
                fp.write(item_value["content"])
                mode = item_value["mode"]
                os.chmod(full_item_path, mode)
                logger.debug("Wrote %s with mode %.4o", full_item_path, mode)

    def default_output_type(self):
        # no output_type options for jinja2
        return None
