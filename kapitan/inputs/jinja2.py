#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os

from kapitan.inputs.base import CompiledFile, InputType
from kapitan.resources import inventory
from kapitan.utils import render_jinja2

logger = logging.getLogger(__name__)


class Jinja2(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("jinja2", compile_path, search_paths, ref_controller)

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

        # set ext_vars and inventory for jinja2 context
        context = ext_vars.copy()
        context["inventory"] = inventory(self.search_paths, target_name)
        context["inventory_global"] = inventory(self.search_paths, None)
        jinja2_filters = kwargs.get("jinja2_filters")

        for item_key, item_value in render_jinja2(
            file_path, context, jinja2_filters=jinja2_filters, search_paths=self.search_paths
        ).items():
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
