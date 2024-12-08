#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os

from kapitan import cached
from kapitan.inputs.base import CompiledFile, InputType
from kapitan.inventory.model.input_types import KapitanInputTypeJinja2Config
from kapitan.utils import render_jinja2

logger = logging.getLogger(__name__)


class Jinja2(InputType):

    def compile_file(self, config: KapitanInputTypeJinja2Config, input_path, compile_path):
        """
        Compile Jinja2 templates.

        Write items in ``input_path`` as Jinja2 rendered files to ``compile_path``.
        ``input_path`` can be either a file or directory.  The rendered files will be written
        to ``compile_path``.

        Args:
            config (KapitanInputTypeJinja2Config): Jinja2 input configuration.
            input_path (str): Path to the input Jinja2 template file or directory.
            compile_path (str): Path to write the compiled files.

        See ``kapitan.inputs.base.InputType`` for details on ``reveal`` and ``target_name``.
        """
        strip_postfix = config.suffix_remove
        stripped_postfix = config.suffix_stripped
        input_params = config.input_params

        reveal = self.args.reveal
        target_name = self.target_name

        # set compile_path allowing jsonnet to have context on where files
        # are being compiled during the current Kapitan run.  This is only done if the user
        # did not provide their own value.
        input_params.setdefault("compile_path", compile_path)

        # set ext_vars and inventory for jinja2 context
        context = {}

        context["inventory_global"] = cached.global_inv
        context["inventory"] = cached.global_inv[target_name]
        context["input_params"] = input_params
        vars = cached.global_inv[target_name]["parameters"]["kapitan"]["vars"]
        context.update(vars)

        jinja2_filters = self.args.jinja2_filters

        for item_key, item_value in render_jinja2(
            input_path, context, jinja2_filters=jinja2_filters, search_paths=self.search_paths
        ).items():
            if strip_postfix and item_key.endswith(stripped_postfix):
                item_key = item_key.rstrip(stripped_postfix)
            full_item_path = os.path.join(compile_path, item_key)
            with CompiledFile(
                full_item_path, self.ref_controller, mode="w", reveal=reveal, target_name=target_name
            ) as fp:
                fp.write(item_value["content"])
                mode = item_value["mode"]
                os.chmod(full_item_path, mode)
                logger.debug("Wrote %s with mode %.4o", full_item_path, mode)
