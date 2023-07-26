#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import sys

# def setup_logging(name=None, level=logging.INFO, force=False):
#     "setup logging and deal with logging behaviours in MacOS python 3.8 and below"
#     # default opts
#     kwopts = {"format": "%(message)s", "level": level}

#     if level == logging.DEBUG:
#         kwopts["format"] = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"

#     if sys.version_info >= (3, 8) and force:
#         kwopts["force"] = True

#     logging.basicConfig(**kwopts)

#     if sys.version_info < (3, 8) and force:
#         logging.getLogger(name).setLevel(level)

#!/usr/bin/env python

"""
Copyright 2023 neXenio
"""

import logging
import os
import sys


def setup_logging(argv):
    "setup logging and deal with logging behaviours in MacOS python 3.8 and below"

    # parse args
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    quiet = "-q" in sys.argv or "--quiet" in sys.argv
    color = "--no-color" not in sys.argv

    # setup logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # log line templates
    log_line_info = "%(color_on)s%(message)s%(color_off)s"
    log_line_debug = (
        "%(color_on)s%(asctime)s %(levelname)-8s %(message)s (%(filename)s:%(lineno)d)%(color_off)s"
    )

    # get level
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
        console_log_template = log_line_debug
    elif quiet:
        level = logging.ERROR
        console_log_template = log_line_info
    else:
        console_log_template = log_line_info

    # setup console handler
    console_log_output = sys.stdout
    console_handler = logging.StreamHandler(console_log_output)
    console_handler.setLevel(level)

    console_formatter = LogFormatter(fmt=console_log_template, color=color)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # setup log file handler
    # if log_file:
    #     # check if log path is valid
    #     parts = log_file.split(os.sep)
    #     if len(parts) > 1:
    #         path = os.sep.join(parts[0:-1])
    #         os.makedirs(path, exist_ok=True)

    #     logfile_handler = logging.FileHandler(log_file + ".log", mode="w")
    #     logfile_handler.setLevel(logging.DEBUG)

    #     logfile_formatter = LogFormatter(fmt=log_line_debug, color=False)
    #     logfile_handler.setFormatter(logfile_formatter)
    #     logger.addHandler(logfile_handler)

    if verbose and quiet:
        logger.warning("Got '--verbose' and '--quiet' as arguments. Using mode: verbose")
    logger.debug(f"Using logging level: {logging.getLevelName(level)}")

    return logger


class LogFormatter(logging.Formatter):
    """
    supports colored formatting
    """

    COLOR_CODES = {
        logging.CRITICAL: "\033[1;35m",  # bright/bold magenta
        logging.ERROR: "\033[1;31m",  # bright/bold red
        logging.WARNING: "\033[1;33m",  # bright/bold yellow
        logging.INFO: "\033[0;37m",  # white / light gray
        logging.DEBUG: "\033[1;30m",  # bright/bold black / dark gray
    }

    RESET_CODE = "\033[0m"

    def __init__(self, color, *args, **kwargs):
        super(LogFormatter, self).__init__(*args, **kwargs)
        self.color = color

    def format(self, record, *args, **kwargs):
        if self.color == True and record.levelno in self.COLOR_CODES:
            record.color_on = self.COLOR_CODES[record.levelno]
            record.color_off = self.RESET_CODE
        else:
            record.color_on = ""
            record.color_off = ""
        return super(LogFormatter, self).format(record, *args, **kwargs)


# XXX in MacOS, updating logging level in __main__ doesn't work for python3.8+
# XXX this is a hack that seems to work
setup_logging(sys.argv)

# Adding reclass to PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__) + "/reclass")
