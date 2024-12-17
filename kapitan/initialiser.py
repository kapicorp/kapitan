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

from kapitan.errors import KapitanError
from kapitan.version import VERSION as kapitan_version

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
        raise KapitanError(f"Directory {directory} is not empty. Please initialise in an empty directory.")

    logger.info(f"Initialising kapitan from {template_git_url}@{checkout_ref} in {directory}")
    user_defaults = {
        "kapitan_version": kapitan_version,
    }
    run_copy(
        template_git_url,
        vcs_ref=args.checkout_ref,
        unsafe=True,
        dst_path=directory,
        quiet=True,
        user_defaults=user_defaults,
        skip_answered=False,
    )

    if directory == os.path.abspath(os.path.curdir):
        logger.info(f"Successfully initialised: run `kapitan --version`")
    else:
        logger.info(f"Successfully initialised kapitan in {directory}")
        logger.info("Please go to the directory and run `kapitan --version`")
