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
        # Propagate HOME and PATH environment variables to external tool
        # This is necessary, because calling `subprocess.run()` with `env` set doesn't propagate
        # any environment variables from the current process.
        # We only propagate HOME or PATH if they're present in Kapitan's environment, but aren't
        # explicitly specified in the input's env_vars already. This ensures we don't run into
        # issues when spawning the subprocess due to `None` values being present in the subprocess's
        # environment.
        if "PATH" not in env_vars and "PATH" in os.environ:
            env_vars["PATH"] = os.environ["PATH"]
        if "HOME" not in env_vars and "HOME" in os.environ:
            env_vars["HOME"] = os.environ["HOME"]
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
            compiled_target_pattern = re.compile(r"(\${compiled_target_dir})")
            args = compiled_target_pattern.sub(compile_path, args)
            # substitute `${compiled_target_dir}` in provided environment variables
            env_vars = {k: compiled_target_pattern.sub(compile_path, v) for (k, v) in self.env_vars.items()}

            logger.debug("Executing external input with command '%s' and env vars '%s'.", args, env_vars)

            external_result = subprocess.run(
                args,
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                encoding="utf8",
            )

            logger.debug("External stdout: %s.", external_result.stdout)
            if external_result.returncode != 0:
                raise ValueError(
                    "Executing external input with command '{}' and env vars '{}' failed: {}".format(
                        args, env_vars, external_result.stderr
                    )
                )

        except OSError as e:
            logger.exception("External failed to run. Error: %s", e)

    def default_output_type(self):
        # no output_type options for external
        return None
