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
import os
import unittest
import tempfile
import yaml

from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.errors import KubernetesManifestValidationError
from kapitan.validator.kubernetes_validator import KubernetesManifestValidator


class KubernetesValidatorTest(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()
        self.validator = KubernetesManifestValidator(self.cache_dir)

    def test_download_and_cache(self):
        downloaded_schema = self.validator._get_schema_from_web('service', '1.14.0')
        self.validator._cache_schema('service', '1.14.0', downloaded_schema)
        self.assertTrue(os.path.isfile(os.path.join(self.cache_dir, 'v1.14.0-standalone-strict', 'service.json')))

    def test_load_from_cache(self):
        kind = 'deployment'
        version = '1.11.0'
        downloaded_schema = self.validator._get_schema_from_web(kind, version)
        self.validator._cache_schema(kind, version, downloaded_schema)
        self.assertIsInstance(self.validator._get_cached_schema(kind, version), dict)

    def test_validate(self):
        service_manifest_string = """
            apiVersion: v1
            kind: Service
            metadata:
              name: my-service
            spec:
              selector:
                app: MyApp
              ports:
              - protocol: TCP
                port: 80
                targetPort: 9376
        """

        service_manifest = yaml.safe_load(service_manifest_string)
        self.validator.validate(service_manifest, kind='service', version='1.14.0')

        with self.assertRaises(KubernetesManifestValidationError):
            self.validator.validate(service_manifest, kind='deployment', version='1.14.0',
                                    file_path='service/manifest', target_name='example')

    def test_compile_with_validate(self):
        pass

    def tearDown(self):
        reset_cache()
