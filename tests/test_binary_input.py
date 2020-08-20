#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"binary input tests"
import os
import sys
import tempfile
import unittest

import yaml
from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.inputs.binary import Binary

YTT_BINARY_PATH = "/usr/local/bin/ytt"


@unittest.skipIf(not os.path.exists(YTT_BINARY_PATH), "ytt binary not found")
class BinaryInputTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join("tests", "test_resources"))

    def test_compile(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "binary-test"]
        main()
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp,
                    "compiled",
                    "binary-test",
                    "extensions.v1beta1.Ingress.default.example-ingress1.yaml",
                )
            )
        )

    def tearDown(self):
        os.chdir("../../")
        reset_cache()
