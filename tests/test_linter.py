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


class LinterTest(unittest.TestCase):
    def test_lint(self):
        num_issues_found = start_lint(
            fail_on_warning=False,
            skip_class_checks=False,
            skip_yamllint=False,
            inventory_path="./tests/test_resources/inventory",
            search_secrets=True,
            secrets_path="./tests/test_resources/secrets",
            compiled_path="./tests/test_resources/compiled",
        )
        desired_output = 3
        self.assertEqual(num_issues_found, desired_output)
