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

"helm input tests"
import os
import unittest
import tempfile
from kapitan.inputs.helm.helm_render import render_chart


class HelmInputTest(unittest.TestCase):
    def test_render_chart(self):
        temp_dir = tempfile.mkdtemp()
        chart_path = "./tests/test_resources/charts/acs-engine-autoscaler"
        render_chart(chart_path, temp_dir)
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "secrets.yaml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "deployment.yaml")))


