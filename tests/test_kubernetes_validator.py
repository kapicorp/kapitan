#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import tempfile
import unittest

from kapitan import defaults
from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.validator.kubernetes_validator import KubernetesManifestValidator
from kapitan.errors import KubernetesManifestValidationError

VALID_MANIFEST = """
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

INVALID_MANIFEST = """
            apiVersion: v1
            kind: Service
            metadata:
              invalid: my-service
            spec:
              selector:
                app: MyApp
              ports:
              - protocol: TCP
                port: 80
                targetPort: 9376
        """

INVALID_WITH_ANNOTATION = """
            apiVersion: v1
            kind: Service
            metadata:
              invalid: my-service
              annotations:
                validation.kapicorp.com/enabled: "false"
            spec:
              selector:
                app: MyApp
              ports:
              - protocol: TCP
                port: 80
                targetPort: 9376
        """

INVALID_WITH_ANNOTATION_TRUE = """
            apiVersion: v1
            kind: Service
            metadata:
              invalid: my-service
              annotations:
                validation.kapicorp.com/enabled: "true"
            spec:
              selector:
                app: MyApp
              ports:
              - protocol: TCP
                port: 80
                targetPort: 9376
        """


class KubernetesValidatorTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join("examples", "kubernetes"))
        self.cache_dir = tempfile.mkdtemp()
        self.validator = KubernetesManifestValidator(self.cache_dir)

    def test_download_and_cache(self):
        kind = "service"
        version = "1.26.0"
        downloaded_schema = self.validator._get_schema_from_web(kind, version)
        self.validator._cache_schema(kind, version, downloaded_schema)
        self.assertTrue(
            os.path.isfile(os.path.join(self.cache_dir, defaults.FILE_PATH_FORMAT.format(version, kind)))
        )

    def test_load_from_cache(self):
        kind = "deployment"
        version = "1.25.0"  # different version just for testing
        downloaded_schema = self.validator._get_schema_from_web(kind, version)
        self.validator._cache_schema(kind, version, downloaded_schema)
        self.assertIsInstance(self.validator._get_cached_schema(kind, version), dict)

    def _get_manifest(self, manifest, filename):
        manifest_path = os.path.join(self.cache_dir, filename)
        with open(manifest_path, "w") as fp:
            fp.write(manifest)
        return manifest_path

    def test_validate(self):
        # None of these should fail
        _VALID = self._get_manifest(VALID_MANIFEST, "service_manifest.yaml")
        _INVALID = self._get_manifest(INVALID_MANIFEST, "service_manifest_invalid.yaml")
        _INVALID_EXCLUDE_KIND = self._get_manifest(INVALID_MANIFEST, "service_manifest_exclude_kind.yaml")
        _INVALID_EXCLUDE_PATH = self._get_manifest(INVALID_MANIFEST, "service_manifest_exclude_path.yaml")
        _INVALID_W_ANNOTATION = self._get_manifest(INVALID_WITH_ANNOTATION, "service_manifest_annotated.yaml")

        objs = list()
        objs.append({"target_name": "test", "output_files": [_VALID]})
        objs.append({"target_name": "test", "output_files": [_INVALID], "fail_on_error": False})
        objs.append(
            {
                "target_name": "test",
                "output_files": [_INVALID_EXCLUDE_KIND],
                "exclude": {"kinds": ["Service"]},
            }
        )
        objs.append(
            {
                "target_name": "test",
                "output_files": [_INVALID_EXCLUDE_PATH],
                "excluded_files": [_INVALID_EXCLUDE_PATH],
            }
        )
        objs.append({"target_name": "test", "output_files": [_INVALID_W_ANNOTATION]})
        self.validator.validate(("1.26.0", objs))

    def test_validate_failure(self):
        # None of these should fail
        _INVALID = self._get_manifest(INVALID_MANIFEST, "service_manifest_invalid.yaml")
        _INVALID_EXCLUDE_KIND = self._get_manifest(INVALID_MANIFEST, "service_manifest_exclude_kind.yaml")
        _INVALID_EXCLUDE_PATH = self._get_manifest(INVALID_MANIFEST, "service_manifest_exclude_path.yaml")
        _INVALID_W_ANNOTATION_TRUE = self._get_manifest(
            INVALID_WITH_ANNOTATION_TRUE, "service_manifest_annotated.yaml"
        )

        validate_objects = [{"target_name": "test", "output_files": [_INVALID]}]
        self.assertRaises(
            KubernetesManifestValidationError, self.validator.validate, ("1.26.0", validate_objects)
        )

        validate_objects = [
            {
                "target_name": "test",
                "output_files": [_INVALID_EXCLUDE_KIND],
                "exclude": {"kinds": ["Deployment"]},
            }
        ]
        self.assertRaises(
            KubernetesManifestValidationError, self.validator.validate, ("1.26.0", validate_objects)
        )

        validate_objects = [
            {
                "target_name": "test",
                "output_files": [_INVALID_EXCLUDE_PATH],
                "excluded_files": ["another_path"],
            }
        ]
        self.assertRaises(
            KubernetesManifestValidationError, self.validator.validate, ("1.26.0", validate_objects)
        )

        validate_objects = [{"target_name": "test", "output_files": [_INVALID_W_ANNOTATION_TRUE]}]
        self.assertRaises(
            KubernetesManifestValidationError, self.validator.validate, ("1.26.0", validate_objects)
        )

    def test_validate_command_pass(self):
        sys.argv = ["kapitan", "validate", "--schemas-path", self.cache_dir]
        try:
            main()
        except SystemExit:
            self.fail("Kubernetes manifest validation error raised unexpectedly")

    def test_validate_after_compile(self):
        sys.argv = [
            "kapitan",
            "compile",
            "-t",
            "minikube-mysql",
            "--validate",
            "--schemas-path",
            self.cache_dir,
        ]
        try:
            main()
        except SystemExit:
            self.fail("Kubernetes manifest validation error raised unexpectedly")

    def tearDown(self):
        os.chdir("../../")
        reset_cache()
