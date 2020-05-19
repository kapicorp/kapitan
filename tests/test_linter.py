#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"linter tests"

import logging
import unittest

from kapitan.lint import start_lint

logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
logger = logging.getLogger(__name__)

"""Helper class for creating args"""


class Object(object):
    pass


class LinterTest(unittest.TestCase):
    def test_lint(self):

        args = Object()
        args.fail_on_warning = False
        args.skip_class_checks = False
        args.skip_yamllint = False
        args.inventory_path = "./tests/test_resources/inventory"
        args.search_secrets = True
        args.refs_path = "./tests/test_resources/secrets"
        args.compiled_path = "./tests/test_resources/compiled"

        num_issues_found = start_lint(args)
        desired_output = 3
        self.assertEqual(num_issues_found, desired_output)
