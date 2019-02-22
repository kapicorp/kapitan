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

"init tests"

import logging
import unittest
import tempfile
import os

from kapitan.initialiser import initialise_skeleton

logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
logger = logging.getLogger(__name__)


class InitTest(unittest.TestCase):
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            initialise_skeleton(directory=tmp_dir)

            template_dir = os.path.join(
                os.getcwd(), 'kapitan', 'inputs', 'templates')

            diff_files = []
            
            for root, dirs, files in os.walk(tmp_dir):
                diff_files += files
            
            for root, dirs, files in os.walk(template_dir):
                for f in files:
                    if f in diff_files:
                        diff_files.remove(f)

            self.assertEqual(len(diff_files), 0)
