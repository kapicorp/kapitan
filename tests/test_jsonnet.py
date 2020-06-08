#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"jsonnet tests"

import json
import os
import unittest

from kapitan.resources import (
    file_exists,
    dir_files_list,
    dir_files_read,
    gzip_b64,
    jsonschema_validate,
    yaml_dump,
    yaml_dump_stream,
    yaml_load,
    yaml_load_stream,
)
from kapitan.utils import prune_empty, sha256_string


class JsonnetNativeFuncsTest(unittest.TestCase):
    def test_yaml_dump(self):
        """dump json string to yaml"""
        yaml = yaml_dump('{"key":"value"}')
        self.assertEqual(yaml, "key: value\n")

    def test_yaml_dump_stream(self):
        """dump json string to yaml"""
        yaml = yaml_dump_stream('[{"key":"value"},{"key":"value"}]')
        self.assertEqual(yaml, "key: value\n---\nkey: value\n")

    def test_file_exists(self):
        """test that file_exists finds this test file"""
        search_paths = [os.getcwd(), "./tests/"]
        result = file_exists(search_paths, "test_jsonnet.py")
        expected = {"exists": True, "path": "./tests/test_jsonnet.py"}
        self.assertEqual(result, expected)

    def test_dir_files_list(self):
        """test if list of files in a dir"""
        search_paths = [os.getcwd(), "./tests/"]
        result = dir_files_list(search_paths, "test_jsonnet")
        expected = ["file1.txt", "file2.txt"]
        self.assertEqual(result.sort(), expected.sort())
        with self.assertRaises(IOError):
            dir_files_list(search_paths, "non_existing_dir")

    def test_dir_files_read(self):
        """must result in dict with key:
        - file_name (contents of the file)"""
        search_paths = [os.getcwd(), "./tests/"]
        result = dir_files_read(search_paths, "test_jsonnet")
        expected = {
            "file1.txt": "To be, or not to be: that is the question",
            "file2.txt": "Nothing will come of nothing.",
        }
        self.assertEqual(result, expected)

    def test_yaml_load(self):
        """
            This tests the yaml_load function.
            It converts the yaml file in test_resources/ to a json string
        """
        current_pwd = os.path.dirname(__file__)
        json = yaml_load([current_pwd], "test_resources/test_yaml_load.yaml")
        expected_output = """{"test": {"key": "value", "array": ["ele1", "ele2"]}}"""
        self.assertEqual(json, expected_output)

    def test_yaml_load_stream(self):
        """
            This tests the yaml_load_stream function.
            It converts the yaml file in test_resources/ to a json string
        """
        current_pwd = os.path.dirname(__file__)
        json = yaml_load_stream([current_pwd], "test_resources/test_yaml_load_stream.yaml")
        expected_output = """[{"test1": {"key": "value", "array": ["ele1", "ele2"]}}, {"test2": {"key": "value", "array": ["ele1", "ele2"]}}]"""
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

    def test_jsonschema_valid(self):
        """validate valid obj with jsonschema"""
        dictionary = {"msg": "hello, world!", "array": [1, 2]}
        schema = {
            "type": "object",
            "properties": {
                "msg": {"type": "string"},
                "array": {"type": "array", "contains": {"type": "number"}},
            },
        }
        validation = jsonschema_validate(json.dumps(dictionary), json.dumps(schema))

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["reason"], "")

    def test_jsonschema_invalid(self):
        """validate invalid obj with jsonschema"""
        dictionary = {"msg": "hello, world!", "array": ["a", "b", "c"]}
        schema = {
            "type": "object",
            "properties": {
                "msg": {"type": "string"},
                "array": {"type": "array", "contains": {"type": "number"}},
            },
        }
        validation = jsonschema_validate(json.dumps(dictionary), json.dumps(schema))

        self.assertFalse(validation["valid"])
        self.assertNotEqual(validation["reason"], "")
