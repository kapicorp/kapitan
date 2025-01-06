#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging

from rich.logging import RichHandler

FORMAT = "%(message)s"


def setup_logging(level=logging.INFO, format=FORMAT, force=False):
    # Console handler: INFO level and above, minimal formatting
    console_handler = RichHandler(logging.INFO, show_level=False, show_path=False, show_time=False)

    # Generic handler: DEBUG level and above (excluding INFO), rich tracebacks
    generic_handler = RichHandler(logging.DEBUG, rich_tracebacks=True)
    generic_handler.setLevel(logging.DEBUG)  # Set the minimum level to DEBUG

    # Add a filter to the generic handler to exclude INFO messages
    class ExcludeInfoFilter(logging.Filter):
        def filter(self, record):
            return record.levelno != logging.INFO

    generic_handler.addFilter(ExcludeInfoFilter())

    logging.basicConfig(
        level=level, force=force, format=format, datefmt="[%X]", handlers=[console_handler, generic_handler]
    )
