#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module"

import logging
import os
from pathlib import Path

from kapitan.utils import tree, copy_tree

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

    logger.info("Populated %s with:", destination)
    for entry in tree(Path(destination), filter_func=lambda x: str(x) in copied_files):
        logger.info(entry)
