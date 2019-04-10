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

"jsonnet tests"

import unittest
import os

from kapitan.resources import *
from kapitan.utils import sha256_string, prune_empty, jsonnet_file

class JsonnetNativeFuncsTest(unittest.TestCase):
    def test_yaml_dump(self):
        """dump json string to yaml"""
        yaml = yaml_dump("{\"key\":\"value\"}")
        self.assertEqual(yaml, "key: value\n")

    def test_yaml_load(self):
        """
            This tests the yaml_load function.
            It converts the yaml file in test_resources/ to a json string
        """
        current_pwd = os.path.dirname(__file__)
        json = yaml_load([current_pwd], "test_resources/test_yaml_load.yaml")
        expected_output = """{"test": {"key": "value", "array": ["ele1", "ele2"]}}"""
        self.assertEqual(json, expected_output)

    def test_sha256_string(self):
        """sha256 hex digest for string"""
        hash = sha256_string("test")
        self.assertEqual(hash, "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")

    def test_gzip_b64(self):
        """base64-encoded gzip-compression for string"""
        gzip = gzip_b64("test")
        self.assertEqual(gzip, "H4sIAAAAAAAC/ytJLS4BAAx+f9gEAAAA")

    def test_prune_empty(self):
        """Remove empty lists and empty dictionaries from dict"""
        dictionary = {"hello": "world", "array": [1, 2], "foo": {}, "bar": []}
        pruned = prune_empty(dictionary)
        self.assertEqual(pruned, {"hello": "world", "array": [1, 2]})

    def test_jsonnet_file(self):
        """ Url import test for jsonnet """
        def _search_imports(cwd, imp):
            return search_imports(cwd, imp, [])

        pwd = os.path.dirname(__file__)
        input_file = "test_resources/test_url_imports_input.jsonnet"
        output_file = "test_resources/test_url_imports_output.json"

        # load rendered jsonnet as json
        input_abs_path = os.path.join(pwd, input_file)
        output_str = jsonnet_file(input_abs_path, import_callback=_search_imports,
                                   native_callbacks=resource_callbacks([]))
        actual_output = json.loads(output_str)

        # load excepted output as json
        output_abs_path = os.path.join(pwd, output_file)
        with open(output_abs_path,'r') as f:
            except_output = json.load(f)

        self.assertEqual(actual_output, except_output)
