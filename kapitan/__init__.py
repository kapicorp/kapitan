#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import logging


def setup_logging(name=None, level=logging.INFO, force=False):
    "setup logging and deal with logging behaviours in MacOS python 3.8 and below"
    # default opts
    kwopts = {"format": "%(message)s", "level": level}

    if level == logging.DEBUG:
        kwopts["format"] = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"

    if sys.version_info >= (3, 8) and force:
        kwopts["force"] = True

    logging.basicConfig(**kwopts)

    if sys.version_info < (3, 8) and force:
        logging.getLogger(name).setLevel(level)


# XXX in MacOS, updating logging level in __main__ doesn't work for python3.8+
# XXX this is a hack that seems to work
if "-v" in sys.argv or "--verbose" in sys.argv:
    setup_logging(level=logging.DEBUG)
else:
    setup_logging()

# Adding reclass to PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__) + "/reclass")
