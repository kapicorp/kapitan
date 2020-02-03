#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import shutil

from kapitan.inputs.base import InputType

logger = logging.getLogger(__name__)


class Copy(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("copy", compile_path, search_paths, ref_controller)

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write items in path as plain rendered files to compile_path.
        path can be either a file or directory.
        """

        try:
            logger.debug("Copying {} to {}.".format(file_path, compile_path))
            if os.path.isfile(file_path):
                if os.path.isfile(compile_path):
                    shutil.copy2(file_path, compile_path)
                else:
                    os.makedirs(compile_path, exist_ok=True)
                    shutil.copy2(file_path, os.path.join(compile_path, os.path.basename(file_path)))
            else:
                if os.path.exists(compile_path):
                    shutil.rmtree(compile_path)
                shutil.copytree(file_path, compile_path)
        except OSError as e:
            logger.exception(f"Input dir not copied. Error: {e}")

    def default_output_type(self):
        # no output_type options for copy
        return None
