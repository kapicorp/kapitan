#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import shutil
from distutils.dir_util import copy_tree

from kapitan.inputs.base import InputType

logger = logging.getLogger(__name__)


class Copy(InputType):
    def __init__(self, compile_path, search_paths, ref_controller, ignore_missing=False):
        self.ignore_missing = ignore_missing
        super().__init__("copy", compile_path, search_paths, ref_controller)

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write items in path as plain rendered files to compile_path.
        path can be either a file or directory.
        """

        # Whether to fail silently if the path does not exists.
        ignore_missing = self.ignore_missing
        try:
            logger.debug("Copying %s to %s.", file_path, compile_path)
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    if os.path.isfile(compile_path):
                        shutil.copy2(file_path, compile_path)
                    else:
                        os.makedirs(compile_path, exist_ok=True)
                        shutil.copy2(file_path, os.path.join(compile_path, os.path.basename(file_path)))
                else:
                    compile_path = os.path.abspath(compile_path)  # Resolve relative paths
                    copy_tree(file_path, compile_path)
            elif ignore_missing == False:
                raise OSError(f"Path {file_path} does not exist and `ignore_missing` is {ignore_missing}")
        except OSError as e:
            logger.exception("Input dir not copied. Error: %s", e)

    def default_output_type(self):
        # no output_type options for copy
        return None
