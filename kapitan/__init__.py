#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys

# this dict is used to confgiure in various places, such as setup spawned processes
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "brief": {"format": "%(message)s"},
        "extended": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"},
    },
    "handlers": {
        "brief": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "brief",
            "stream": "ext://sys.stdout",
        },
        "extended": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "extended",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "kapitan": {"level": "INFO", "propagate": True},
        "reclass": {"level": "INFO", "propagate": True},
    },
    "root": {"level": "ERROR", "handlers": ["brief"]},
}

# Adding reclass to PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__) + "/reclass")
