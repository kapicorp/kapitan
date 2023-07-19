#!/usr/bin/env python

"""
Copyright 2023 neXenio
"""

import logging
import os
import sys


def setup_logging(args):
    "setup logging and deal with logging behaviours in MacOS python 3.8 and below"

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
    if args.verbose:
        level = logging.DEBUG
        console_log_template = log_line_debug
    elif args.quiet:
        level = logging.ERROR
        console_log_template = log_line_info
    else:
        console_log_template = log_line_info

    # setup console handler
    console_log_output = sys.stdout
    console_handler = logging.StreamHandler(console_log_output)
    console_handler.setLevel(level)

    console_formatter = LogFormatter(fmt=console_log_template, color=not args.no_color)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # setup log file handler
    if args.log_file:
        # check if log path is valid
        parts = args.log_file.split(os.sep)
        if len(parts) > 1:
            path = os.sep.join(parts[0:-1])
            os.makedirs(path, exist_ok=True)

        logfile_handler = logging.FileHandler(args.log_file + ".log", mode="w")
        logfile_handler.setLevel(logging.DEBUG)

        logfile_formatter = LogFormatter(fmt=log_line_debug, color=False)
        logfile_handler.setFormatter(logfile_formatter)
        logger.addHandler(logfile_handler)

    if args.verbose and args.quiet:
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

    def get_formatting(self, record):
        """
        return matching formatting depending on the records log level
        """

        # set color schema
        reset = "\x1b[0m"
        COLORS = {
            logging.DEBUG: "\x1b[34;20m{}" + reset,  # blue
            logging.INFO: "{}",  # no color
            logging.WARNING: "\x1b[33;20m{}" + reset,  # yellow
            logging.ERROR: "\x1b[31;20m{}" + reset,  # red
            logging.CRITICAL: "\x1b[31;1m{}" + reset,  # bold red
        }

        # disable coloring
        if self.kwargs.get("no_color"):
            COLORS = {}

        # default format
        log_format = COLORS.get(record.levelno, "{}").format("%(message)s")

        # debug format (--verbose)
        if self.kwargs.get("level") == logging.DEBUG:
            spacing = " " * (8 - len(record.levelname))
            log_format = "%(asctime)s {} %(message)s (%(filename)s:%(lineno)d)".format(
                COLORS.get(record.levelno, "{}").format("%(levelname)s") + spacing
            )

        return log_format
