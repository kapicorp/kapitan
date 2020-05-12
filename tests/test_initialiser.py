#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"init tests"

import logging
import os
import sys
import tempfile
import unittest

from kapitan.cached import reset_cache
from kapitan.cli import main

logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
logger = logging.getLogger(__name__)


class InitTest(unittest.TestCase):
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            sys.argv = ["kapitan", "init", "--directory", tmp_dir]
            main()

            template_dir = os.path.join(os.getcwd(), "kapitan", "inputs", "templates")

            diff_files = []

            for root, dirs, files in os.walk(tmp_dir):
                diff_files += files

            for root, dirs, files in os.walk(template_dir):
                for f in files:
                    if f in diff_files:
                        diff_files.remove(f)

            self.assertEqual(len(diff_files), 0)

            # check that generated directory compiles
            prevdir = os.getcwd()
            os.chdir(tmp_dir)
            sys.argv = ["kapitan", "compile"]
            main()

            os.chdir(prevdir)
            reset_cache()
