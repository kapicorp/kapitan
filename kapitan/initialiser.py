#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module"

import glob
import logging
import os

from copier import run_copy

logger = logging.getLogger(__name__)


def initialise_skeleton(args):
    """Initialises a directory with a recommended skeleton structure using cruft
    Args:
        args.template_git_url (string): path or url that contains the cruft repository template
        args.checkout_ref (string): branch, tag or commit to checkout from the template repository
        args.directory (string): directory to initialise the skeleton in (default is current directory)
    """

    template_git_url = args.template_git_url
    checkout_ref = args.checkout_ref
    directory = os.path.abspath(args.directory)

    if set(glob.iglob(os.path.join(directory, "./*"))):
        logger.error(f"Directory {directory} is not empty. Please initialise in an empty directory.")
        return

    logger.info(f"Initialising skeleton from {template_git_url}@{checkout_ref} in {directory}")
    run_copy(template_git_url, vcs_ref=args.checkout_ref, unsafe=True, dst_path=directory)
