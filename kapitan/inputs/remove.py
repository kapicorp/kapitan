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


class Remove(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("remove", compile_path, search_paths, ref_controller)

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write items in path as plain rendered files to compile_path.
        path can be either a file or directory.
        """

        try:
            logger.debug("Removing %s", file_path)
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                shutil.rmtree(file_path)
        except OSError as e:
            logger.exception("Input dir not removed. Error: %s", e)

    def default_output_type(self):
        # no output_type options for remove
        return None
