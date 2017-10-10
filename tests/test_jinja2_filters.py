#!/usr/bin/python
#
# Copyright 2017 The Kapitan Authors
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

"tests"
import unittest
import tempfile
from kapitan.utils import render_jinja2_file

class Jinja2FiltersTest(unittest.TestCase):
    def test_sha256(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("{{text|sha256}}")
            f.seek(0)
            context = {"text":"this and that"}
            digest = 'e863c1ac42619a2b429a08775a6acd89ff4c2c6b8dae12e3461a5fa63b2f92f5'
            self.assertEqual(render_jinja2_file(f.name, context), digest)
