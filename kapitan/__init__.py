#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import sys


def setup_logging(
    name: str | None = None, level: int = logging.INFO, force: bool = False
) -> None:
    """
    Configure Python logging with appropriate format and level.

    Args:
        name: Logger name (unused, kept for backwards compatibility)
        level: Logging level (default: logging.INFO)
        force: Force reconfiguration of existing loggers
    """
    kwopts: dict[str, str | int | bool] = {"format": "%(message)s", "level": level}

    if level == logging.DEBUG:
        kwopts["format"] = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"

    if force:
        kwopts["force"] = True

    logging.basicConfig(**kwopts)


# Early logging setup based on command-line arguments
if "-v" in sys.argv or "--verbose" in sys.argv:
    setup_logging(level=logging.DEBUG)
else:
    setup_logging()
