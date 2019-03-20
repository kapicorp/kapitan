#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"linter tests"

import logging
import unittest

from kapitan.lint import start_lint

logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
logger = logging.getLogger(__name__)


class LinterTest(unittest.TestCase):
    def test_lint(self):
        num_issues_found = start_lint(fail_on_warning=False,
                            skip_class_checks=False,
                            skip_yamllint=False,
                            inventory_path="./tests/test_resources/inventory",
                            search_secrets=True,
                            secrets_path="./tests/test_resources/secrets",
                            compiled_path="./tests/test_resources/compiled")
        desired_output = 3
        self.assertEqual(num_issues_found, desired_output)
