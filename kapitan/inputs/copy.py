#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import shutil

from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import KapitanInputTypeCopyConfig
from kapitan.utils import copy_tree

logger = logging.getLogger(__name__)


class Copy(InputType):
    def compile_file(self, config: KapitanInputTypeCopyConfig, input_path, compile_path):
        """
        Write items in path as plain rendered files to compile_path.
        path can be either a file or directory.
        """

        # Whether to fail silently if the path does not exists.
        ignore_missing = config.ignore_missing

        try:
            logger.debug("Copying %s to %s.", input_path, compile_path)
            if os.path.exists(input_path):
                if os.path.isfile(input_path):
                    if os.path.isfile(compile_path):
                        shutil.copy2(input_path, compile_path)
                    else:
                        os.makedirs(compile_path, exist_ok=True)
                        shutil.copy2(input_path, os.path.join(compile_path, os.path.basename(input_path)))
                else:
                    compile_path = os.path.abspath(compile_path)  # Resolve relative paths
                    copy_tree(input_path, compile_path)
            elif not ignore_missing:
                raise OSError(f"Path {input_path} does not exist and `ignore_missing` is {ignore_missing}")
        except OSError as e:
            logger.exception("Input dir not copied. Error: %s", e)
