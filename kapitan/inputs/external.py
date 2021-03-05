#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import subprocess
import re
import logging
import os
import shutil
from distutils.dir_util import copy_tree

from kapitan.inputs.base import InputType

logger = logging.getLogger(__name__)


class External(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("external", compile_path, search_paths, ref_controller)
        self.env_vars = {}
        self.args = []
        self.target_name = None

    def set_env_vars(self, env_vars):
        self.env_vars = env_vars

    def set_args(self, args):
        self.args = args

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Execute external with specific arguments and env vars.
        If external exits with non zero error code, error is thrown
        """

        try:
            # file_path (str): Path to executable script or binary
            external_path = file_path

            args = [external_path]
            args.extend(self.args)
            args = " ".join(args)

            # compile_path (str): Path to current target compiled directory
            args = re.sub(r"(\${compiled_target_dir})", compile_path, args)

            logger.debug("Executing external input with command '%s' and env vars '%s'.", args, self.env_vars)

            external_result = subprocess.run(
                args,
                env=self.env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                encoding="utf8",
            )

            logger.debug("External stdout: %s.", external_result.stdout)
            if external_result.returncode != 0:
                raise ValueError(
                    "Executing external input with command '{}' and env vars '{}' failed: {}".format(
                        args, self.env_vars, external_result.stderr
                    )
                )

        except OSError as e:
            logger.exception("External failed to run. Error: %s", e)

    def default_output_type(self):
        # no output_type options for external
        return None
