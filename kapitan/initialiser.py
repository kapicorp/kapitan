#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module"

import logging
import os
from pathlib import Path

from kapitan.utils import copy_tree

logger = logging.getLogger(__name__)


def initialise_skeleton(args):
    """Initialises a directory with a recommended skeleton structure and prints list of
    copied files.

    Args:
        args.directory (string): path which to initialise, directory is assumed to exist.
    """
    templates = Path(__file__).resolve().parent.joinpath("inputs", "templates")
    destination = Path(args.directory)
    copied_files = copy_tree(source=templates, destination=destination, dirs_exist_ok=True)

    logger.info("Populated %s with:", args.directory)
    for directory, _, file_list in os.walk(args.directory):
        # In order to avoid adding the given directory itself in listing.
        if directory == args.directory:
            continue
        if any([path.startswith(directory) for path in copied_files]):
            level = directory.replace(args.directory, "").count(os.sep) - 1
            indent = " " * 4 * (level)
            logger.info("%s%s", indent, os.path.basename(directory))
            for fname in file_list:
                if os.path.join(directory, fname) in copied_files:
                    sub_indent = " " * 4 * (level + 1)
                    logger.info("%s%s", sub_indent, fname)
