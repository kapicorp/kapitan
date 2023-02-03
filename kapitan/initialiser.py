#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module"

import logging
import os
from distutils.dir_util import copy_tree

logger = logging.getLogger(__name__)


def initialise_skeleton(args):
    """Initialises a directory with a recommended skeleton structure
    Args:
        args.directory (string): path which to initialise, directory is assumed to exist
    """

    current_pwd = os.path.dirname(__file__)
    templates_directory = os.path.join(current_pwd, "inputs", "templates")
    populated = copy_tree(templates_directory, args.directory)
    logger.info("Populated %s with:", args.directory)
    for directory, subs, file_list in os.walk(args.directory):
        # In order to avoid adding the given directory itself in listing.
        if directory == args.directory:
            continue
        if any([path.startswith(directory) for path in populated]):
            level = directory.replace(args.directory, "").count(os.sep) - 1
            indent = " " * 4 * (level)
            logger.info("%s%s", indent, os.path.basename(directory))
            for fname in file_list:
                if os.path.join(directory, fname) in populated:
                    sub_indent = " " * 4 * (level + 1)
                    logger.info("%s%s", sub_indent, fname)
