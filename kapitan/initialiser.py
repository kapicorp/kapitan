#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module"

import logging
from copier import run_copy
import glob

logger = logging.getLogger(__name__)


def initialise_skeleton(args):
    """Initialises a directory with a recommended skeleton structure using cruft
    Args:
        args.template_git_url (string): path or url that contains the cruft repository template
        args.checkout_ref (string): branch, tag or commit to checkout from the template repository
    """
    
    template_git_url = args.template_git_url
    if set(glob.iglob("./*")):
        logger.error("Directory is not empty. Please initialise in an empty directory.")
        return
    
    logger.info(f"Initialising skeleton from {template_git_url}")
    run_copy(template_git_url, vcs_ref=args.checkout_ref, unsafe=True)