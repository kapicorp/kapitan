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

logger = logging.getLogger(__name__)


class Remove(InputType):

    def compile_file(self, config: KapitanInputTypeCopyConfig, input_path, compile_path):
        """Remove a file or directory.

        Args:
            config (KapitanInputTypeCopyConfig): input type configuration
            input_path (str): path to file or directory to remove
            compile_path (str): not used in this input type

        Raises:
            OSError: if the file or directory cannot be removed
        """

        try:
            logger.debug("Removing %s", input_path)
            if os.path.isfile(input_path):
                os.remove(input_path)
            else:
                shutil.rmtree(input_path)
        except OSError as e:
            logger.exception("Input dir not removed. Error: %s", e)
