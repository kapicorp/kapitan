#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
                    shutil.copy2(file_path, os.path.join(
                        compile_path, os.path.basename(file_path)))
            else:
                if os.path.exists(compile_path):
                    shutil.rmtree(compile_path)
                shutil.copytree(file_path, compile_path)
        except OSError as e:
            logger.exception("Input dir not copied. Error: {}".format(e))

    def default_output_type(self):
        # no output_type options for copy
        return None
