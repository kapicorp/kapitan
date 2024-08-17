#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module"

import logging
import cruft

logger = logging.getLogger(__name__)


def initialise_skeleton(args):
    """Initialises a directory with a recommended skeleton structure using cruft
    Args:
        args.template_git_url (string): path or url that contains the cruft repository template
        args.checkout_ref (string): branch, tag or commit to checkout from the template repository
    """
    
    template_git_url = args.template_git_url
    checkout_ref = args.checkout_ref
    
    cruft.create(
        template_git_url=template_git_url,
        checkout=checkout_ref,
    )
