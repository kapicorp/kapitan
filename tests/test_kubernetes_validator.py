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
from shutil import copyfile
import sys
import unittest
import tempfile
import yaml
from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.errors import KubernetesManifestValidationError
from kapitan.validator.kubernetes_validator import KubernetesManifestValidator, FILE_PATH_FORMAT


class KubernetesValidatorTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join('examples', 'kubernetes'))
        self.cache_dir = tempfile.mkdtemp()
        self.validator = KubernetesManifestValidator(self.cache_dir)

    def test_download_and_cache(self):
        kind = 'service'
        version = '1.14.0'
        downloaded_schema = self.validator._get_schema_from_web(kind, version)
        self.validator._cache_schema(kind, version, downloaded_schema)
        self.assertTrue(os.path.isfile(os.path.join(self.cache_dir, FILE_PATH_FORMAT.format(version, kind))))

    def test_load_from_cache(self):
        kind = 'deployment'
        version = '1.11.0'  # different version just for testing
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
        manifest_path = os.path.join(self.cache_dir, 'service_manifest.yaml')
        with open(manifest_path, 'w') as fp:
            fp.write(service_manifest_string)
        self.validator.validate([manifest_path], kind='service', version='1.14.0')

        with self.assertRaises(KubernetesManifestValidationError):
            self.validator.validate([manifest_path], kind='deployment', version='1.14.0')

    def test_validate_command_pass(self):
        sys.argv = ['kapitan', 'validate', '--schemas-path', self.cache_dir]
        try:
            main()
        except SystemExit:
            self.fail("Kubernetes manifest validation error raised unexpectedly")

    def test_validate_command_fail(self):
        file_name_format = 'inventory/classes/component/mysql{}.yml'
        original_file = file_name_format.format('')
        copied_file = file_name_format.format('_copy')
        copyfile(original_file, copied_file)
        wrong_manifest_kind = 'deployment'
        with open(original_file, 'r') as fp:
            d = yaml.safe_load(fp)
            # change kind from service to deployment
            d['parameters']['kapitan']['validate'][0]['kind'] = wrong_manifest_kind
        with open(original_file, 'w') as fp:
            yaml.dump(d, fp, default_flow_style=False)

        sys.argv = ['kapitan', 'validate', '--schemas-path', self.cache_dir]
        with self.assertRaises(SystemExit), self.assertLogs(logger='kapitan.targets', level='ERROR') as log:
            try:
                main()
            finally:
                # copy back the original file
                copyfile(copied_file, original_file)
                os.remove(copied_file)
        self.assertTrue(' '.join(log.output).find("invalid '{}' manifest".format(wrong_manifest_kind)) != -1)

    def test_validate_after_compile(self):
        sys.argv = ['kapitan', 'compile', '-t', 'minikube-mysql', '--validate', '--schemas-path', self.cache_dir]
        try:
            main()
        except SystemExit:
            self.fail("Kubernetes manifest validation error raised unexpectedly")

    def tearDown(self):
        os.chdir('../../')
        reset_cache()
