#!/usr/bin/env python3.6
#
# Copyright 2018 The Kapitan Authors
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

"jsonnet tests"

import unittest
from kapitan.resources import yaml_dump


class JsonnetNativeFuncsTest(unittest.TestCase):
    def test_yaml_dump(self):
        "dump json string to yaml"
        yaml = yaml_dump("{\"key\":\"value\"}")
        self.assertEqual(yaml, "key: value\n")
