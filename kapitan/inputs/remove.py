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
        """
        Write items in path as plain rendered files to compile_path.
        path can be either a file or directory.
        """

        try:
            logger.debug("Removing %s", input_path)
            if os.path.isfile(input_path):
                os.remove(input_path)
            else:
                shutil.rmtree(input_path)
        except OSError as e:
            logger.exception("Input dir not removed. Error: %s", e)
