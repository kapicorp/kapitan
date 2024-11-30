#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import re
import subprocess
from typing import Dict, List

from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import KapitanInputTypeExternalConfig

logger = logging.getLogger(__name__)


class External(InputType):
    """
    External input type. Executes an external command to generate Kubernetes manifests.
    """

    env_vars: Dict[str, str] = {}  #: Environment variables to pass to the external command.
    command_args: List[str] = []  #: Command-line arguments to pass to the external command.

    def set_env_vars(self, env_vars):
        """
        Sets environment variables for the external command.
        Propagates HOME and PATH environment variables if they are not explicitly set.
        This is necessary because `subprocess.run()` with `env` set doesn't propagate
        environment variables from the current process.  We only propagate HOME or PATH if they
        exist in the Kapitan environment but aren't explicitly specified in `env_vars`. This
        prevents issues when spawning the subprocess due to `None` values in the subprocess's
        environment.
        """
        if "PATH" not in env_vars and "PATH" in os.environ:
            env_vars["PATH"] = os.environ["PATH"]
        if "HOME" not in env_vars and "HOME" in os.environ:
            env_vars["HOME"] = os.environ["HOME"]
        self.env_vars = env_vars

    def set_args(self, args: List[str]):
        """Sets command-line arguments for the external command."""
        self.command_args = args

    def compile_file(self, config: KapitanInputTypeExternalConfig, input_path, compile_path):
        """
        Execute external with specific arguments and env vars.
        If the external command exits with a non-zero error code, an error is raised.
        Args:
            config: KapitanInputTypeExternalConfig object.
            input_path: Path to the external command.
            compile_path: Path to the compiled target directory.
        """

        try:
            # file_path (str): Path to executable script or binary
            external_path = input_path

            self.set_args(config.args)
            self.set_env_vars(config.env_vars)

            args = [external_path]
            args.extend(self.command_args)
            args_str = " ".join(args)  # join args for logging and substitution

            # Substitute `${compiled_target_dir}` in the command arguments and environment variables.
            compiled_target_pattern = re.compile(r"(\${compiled_target_dir})")
            args_str = compiled_target_pattern.sub(compile_path, args_str)
            env_vars = {k: compiled_target_pattern.sub(compile_path, v) for (k, v) in config.env_vars.items()}

            # Run the external command.  shell=True is required for argument substitution to work correctly.
            # However, this introduces a security risk if the input_path or command_args are not properly sanitized.
            # Consider using the shlex module to properly quote and escape arguments to mitigate this risk.
            # See https://docs.python.org/3/library/shlex.html for more information.

            logger.debug("Executing external input with command '%s' and env vars '%s'.", args, env_vars)

            external_result = subprocess.run(
                args_str,
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                encoding="utf-8",
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
