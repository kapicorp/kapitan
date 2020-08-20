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


class Binary(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("binary", compile_path, search_paths, ref_controller)
        self.binary_env_vars = {}
        self.binary_args = []
        self.target_name = None

    def set_binary_env_vars(self, binary_env_vars):
        self.binary_env_vars = binary_env_vars

    def set_binary_args(self, binary_args):
        self.binary_args = binary_args

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Execute binary with specific arguments and env vars.
        If binary exits with non zero error code, error is thrown
        """

        try:
            binary_path = file_path

            args = [binary_path]
            args.extend(self.binary_args)
            args = " ".join(args)

            args = re.sub(r"(\${compiled_target_dir})", compile_path, args)

            logger.debug(
                "Executing binary input with command '{}' and env vars '{}'.".format(
                    args, self.binary_env_vars
                )
            )

            binary_result = subprocess.run(
                args,
                env=self.binary_env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                encoding="utf8",
            )

            logger.debug("Binary stdout: {}.".format(binary_result.stdout))
            if binary_result.returncode != 0:
                raise ValueError(
                    "Executing binary input with command '{}' and env vars '{}' failed: {}".format(
                        args, self.binary_env_vars, binary_result.stderr
                    )
                )

        except OSError as e:
            logger.exception(f"Binary failed to run. Error: {e}")

    def default_output_type(self):
        # no output_type options for copy
        return None
