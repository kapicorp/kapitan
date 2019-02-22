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

"initialiser module"

import logging
import os
import sys
import shutil
from distutils.dir_util import copy_tree

logger = logging.getLogger(__name__)

def initialise_skeleton(directory):
    """ Initialises a directory with a recommended skeleton structure
    Args:
        directory (string): path which to initialise, directory is assumed to exist
    """

    current_pwd = os.path.dirname(__file__)
    templates_directory = os.path.join(current_pwd, 'inputs', 'templates')

    copy_tree(templates_directory, directory)

    logger.info("Populated {} with:".format(directory))
    for dirName, subdirList, fileList in os.walk(directory):
        logger.info('{}'.format(dirName))
        for fname in fileList:
            logger.info('\t {}'.format(fname))
        # Remove the first entry in the list of sub-directories
        # if there are any sub-directories present
        if len(subdirList) > 0:
            del subdirList[0]
