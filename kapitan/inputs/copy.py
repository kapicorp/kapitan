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
        """Copy input_path to compile_path.

        Args:
            config (KapitanInputTypeCopyConfig): input configuration.
            input_path (str): path to the file or directory to copy.
            compile_path (str): path to the destination directory.

        Raises:
            OSError: if input_path does not exist and ignore_missing is False.
        """

        ignore_missing = config.ignore_missing

        try:
            if os.path.exists(input_path):
                logger.debug("Copying '%s' to '%s'.", input_path, compile_path)
                if os.path.isfile(input_path):
                    if os.path.isfile(compile_path):
                        # overwrite existing file
                        shutil.copy2(input_path, compile_path)
                    else:
                        # create destination directory if it doesn't exist
                        os.makedirs(compile_path, exist_ok=True)
                        # copy file to destination directory
                        shutil.copy2(input_path, os.path.join(compile_path, os.path.basename(input_path)))
                else:
                    # Resolve relative paths to avoid issues with copy_tree
                    compile_path = os.path.abspath(compile_path)  # Resolve relative paths
                    copy_tree(input_path, compile_path)
            elif not ignore_missing:
                # Raise exception if input path does not exist and ignore_missing is False
                raise OSError(f"Path {input_path} does not exist and `ignore_missing` is {ignore_missing}")
        except OSError as e:
            # Log exception and re-raise
            logger.exception("Input dir not copied. Error: %s", e)
