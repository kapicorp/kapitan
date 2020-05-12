#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module"

import logging
import os
from distutils.dir_util import copy_tree

logger = logging.getLogger(__name__)


def initialise_skeleton(args):
    """ Initialises a directory with a recommended skeleton structure
    Args:
        args.directory (string): path which to initialise, directory is assumed to exist
    """

    current_pwd = os.path.dirname(__file__)
    templates_directory = os.path.join(current_pwd, "inputs", "templates")

    copy_tree(templates_directory, args.directory)

    logger.info("Populated {} with:".format(args.directory))
    for dirName, subdirList, fileList in os.walk(args.directory):
        logger.info("{}".format(dirName))
        for fname in fileList:
            logger.info("\t {}".format(fname))
        # Remove the first entry in the list of sub-directories
        # if there are any sub-directories present
        if len(subdirList) > 0:
            del subdirList[0]
