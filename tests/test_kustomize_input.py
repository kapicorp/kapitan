#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for Kustomize input type."""

import os
import shutil
import tempfile
import unittest

import yaml
from pydantic import ValidationError

from kapitan.errors import KustomizeTemplateError
from kapitan.inputs.kustomize import Kustomize
from kapitan.inventory.model.input_types import KapitanInputTypeKustomizeConfig


class KustomizeInputTest(unittest.TestCase):
    """Test cases for Kustomize input type."""

    def setUp(self):
        """Set up test environment."""
        self.compile_path = tempfile.mkdtemp()
        self.search_paths = []
        self.ref_controller = None
        self.target_name = "test-target"
        self.args = type(
            "Args",
            (),
            {"kustomize_path": "kustomize", "reveal": False, "indent": 2},
        )
        self.kustomize = Kustomize(
            self.compile_path,
            self.search_paths,
            self.ref_controller,
            self.target_name,
            self.args,
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.compile_path)

    def test_compile_file_with_patches(self):
        """Test compiling a Kustomize overlay with patches."""
        # Create a temporary directory for the test
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a basic kustomization.yaml
            kustomization = {
                "resources": ["deployment.yaml"],
                "namespace": "test-namespace",
            }
            with open(os.path.join(temp_dir, "kustomization.yaml"), "w") as f:
                yaml.dump(kustomization, f)

            # Create a basic deployment.yaml
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "test-deployment",
                    "namespace": "test-namespace",
                },
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "test-container",
                                    "image": "nginx:latest",
                                }
                            ]
                        }
                    }
                },
            }
            with open(os.path.join(temp_dir, "deployment.yaml"), "w") as f:
                yaml.dump(deployment, f)

            # Create a patch
            patch = {
                "target": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "test-namespace",
                },
                "patch": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {
                        "name": "test-deployment",
                        "namespace": "test-namespace",
                    },
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "test-container",
                                        "image": "nginx:1.19",
                                    }
                                ]
                            }
                        }
                    },
                },
            }

            # Create config
            config = KapitanInputTypeKustomizeConfig(
                namespace="test-namespace",
                patches={"image-patch": patch},
                input_paths=[temp_dir],
                output_path=self.compile_path,
            )

            # Compile the overlay
            self.kustomize.compile_file(config, temp_dir, self.compile_path)

            # Verify the output
            output_file = os.path.join(
                self.compile_path, "test-deployment-deployment.yaml"
            )
            self.assertTrue(os.path.exists(output_file))

            with open(output_file) as f:
                output = yaml.safe_load(f)
                self.assertEqual(
                    output["spec"]["template"]["spec"]["containers"][0]["image"],
                    "nginx:1.19",
                )

        finally:
            shutil.rmtree(temp_dir)

    def test_compile_file_with_namespace(self):
        """Test compiling a Kustomize overlay with namespace."""
        # Create a temporary directory for the test
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a basic kustomization.yaml
            kustomization = {
                "resources": ["deployment.yaml"],
            }
            with open(os.path.join(temp_dir, "kustomization.yaml"), "w") as f:
                yaml.dump(kustomization, f)

            # Create a basic deployment.yaml
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "test-deployment",
                },
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "test-container",
                                    "image": "nginx:latest",
                                }
                            ]
                        }
                    }
                },
            }
            with open(os.path.join(temp_dir, "deployment.yaml"), "w") as f:
                yaml.dump(deployment, f)

            # Create config
            config = KapitanInputTypeKustomizeConfig(
                namespace="test-namespace",
                input_paths=[temp_dir],
                output_path=self.compile_path,
            )

            # Compile the overlay
            self.kustomize.compile_file(config, temp_dir, self.compile_path)

            # Verify the output
            output_file = os.path.join(
                self.compile_path, "test-deployment-deployment.yaml"
            )
            self.assertTrue(os.path.exists(output_file))

            with open(output_file) as f:
                output = yaml.safe_load(f)
                self.assertEqual(
                    output["metadata"]["namespace"],
                    "test-namespace",
                )

        finally:
            shutil.rmtree(temp_dir)

    def test_compile_file_with_invalid_input(self):
        """Test compiling a Kustomize overlay with invalid input."""
        # Create a temporary directory for the test
        temp_dir = tempfile.mkdtemp()
        try:
            # Create an invalid kustomization.yaml
            kustomization = {
                "resources": ["nonexistent.yaml"],
            }
            with open(os.path.join(temp_dir, "kustomization.yaml"), "w") as f:
                yaml.dump(kustomization, f)

            # Create config
            config = KapitanInputTypeKustomizeConfig(
                namespace="test-namespace",
                input_paths=[temp_dir],
                output_path=self.compile_path,
            )

            # Compile the overlay and expect an error
            with self.assertRaises(KustomizeTemplateError):
                self.kustomize.compile_file(config, temp_dir, self.compile_path)

        finally:
            shutil.rmtree(temp_dir)

    def test_compile_file_with_invalid_patch(self):
        """Test compiling a Kustomize overlay with invalid patch."""
        # Create a temporary directory for the test
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a basic kustomization.yaml
            kustomization = {
                "resources": ["deployment.yaml"],
            }
            with open(
                os.path.join(temp_dir, "kustomization.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(kustomization, f)

            # Create a basic deployment.yaml
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "test-deployment",
                },
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "test-container",
                                    "image": "nginx:latest",
                                }
                            ]
                        }
                    }
                },
            }
            with open(
                os.path.join(temp_dir, "deployment.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(deployment, f)

            # Create an invalid patch
            patch = {
                "target": {
                    "kind": "Deployment",
                    "name": "nonexistent-deployment",
                },
                "patch": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {
                        "name": "nonexistent-deployment",
                    },
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "test-container",
                                        "image": "nginx:1.19",
                                    }
                                ]
                            }
                        }
                    },
                },
            }

            # Create config
            config = KapitanInputTypeKustomizeConfig(
                namespace="test-namespace",
                patches={"invalid-patch": patch},
                input_paths=[temp_dir],
                output_path=self.compile_path,
            )

            # Compile the overlay
            self.kustomize.compile_file(config, temp_dir, self.compile_path)

            # Verify the output
            output_file = os.path.join(
                self.compile_path, "test-deployment-deployment.yaml"
            )
            self.assertTrue(os.path.exists(output_file))

            # Verify that the patch was not applied (image should still be nginx:latest)
            with open(output_file, encoding="utf-8") as f:
                output = yaml.safe_load(f)
                self.assertEqual(
                    output["spec"]["template"]["spec"]["containers"][0]["image"],
                    "nginx:latest",
                )

        finally:
            shutil.rmtree(temp_dir)

    def test_compile_file_with_output_file(self):
        """Test compiling a Kustomize overlay with output_file set."""
        temp_dir = tempfile.mkdtemp()
        try:
            kustomization = {
                "resources": ["deployment.yaml"],
            }
            with open(
                os.path.join(temp_dir, "kustomization.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(kustomization, f)

            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "test-deployment"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {"name": "test-container", "image": "nginx:latest"}
                            ]
                        }
                    }
                },
            }
            with open(
                os.path.join(temp_dir, "deployment.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(deployment, f)

            config = KapitanInputTypeKustomizeConfig(
                namespace="test-namespace",
                input_paths=[temp_dir],
                output_path=self.compile_path,
                output_file="install.yml",
            )

            self.kustomize.compile_file(config, temp_dir, self.compile_path)

            output_file = os.path.join(self.compile_path, "install.yml")
            self.assertTrue(os.path.exists(output_file))

            # Should be raw multi-document YAML, not a single parsed doc
            with open(output_file, encoding="utf-8") as f:
                content = f.read()
            docs = list(yaml.safe_load_all(content))
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0]["metadata"]["name"], "test-deployment")
        finally:
            shutil.rmtree(temp_dir)

    def test_compile_file_with_nested_output_file(self):
        """Test compiling with a nested output_file path."""
        temp_dir = tempfile.mkdtemp()
        try:
            kustomization = {
                "resources": ["deployment.yaml"],
            }
            with open(
                os.path.join(temp_dir, "kustomization.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(kustomization, f)

            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "test-deployment"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {"name": "test-container", "image": "nginx:latest"}
                            ]
                        }
                    }
                },
            }
            with open(
                os.path.join(temp_dir, "deployment.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(deployment, f)

            config = KapitanInputTypeKustomizeConfig(
                input_paths=[temp_dir],
                output_path=self.compile_path,
                output_file="bundles/install.yml",
            )

            self.kustomize.compile_file(config, temp_dir, self.compile_path)

            output_file = os.path.join(self.compile_path, "bundles", "install.yml")
            self.assertTrue(os.path.exists(output_file))
        finally:
            shutil.rmtree(temp_dir)

    def test_compile_file_without_output_file_splits_resources(self):
        """Test that default behavior still splits resources when output_file is unset."""
        temp_dir = tempfile.mkdtemp()
        try:
            kustomization = {
                "resources": ["deployment.yaml", "service.yaml"],
            }
            with open(
                os.path.join(temp_dir, "kustomization.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(kustomization, f)

            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "test-deployment"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {"name": "test-container", "image": "nginx:latest"}
                            ]
                        }
                    }
                },
            }
            with open(
                os.path.join(temp_dir, "deployment.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(deployment, f)

            service = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": "test-service"},
                "spec": {"ports": [{"port": 80}]},
            }
            with open(
                os.path.join(temp_dir, "service.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(service, f)

            config = KapitanInputTypeKustomizeConfig(
                input_paths=[temp_dir],
                output_path=self.compile_path,
            )

            self.kustomize.compile_file(config, temp_dir, self.compile_path)

            deployment_file = os.path.join(
                self.compile_path, "test-deployment-deployment.yaml"
            )
            service_file = os.path.join(self.compile_path, "test-service-service.yaml")
            self.assertTrue(os.path.exists(deployment_file))
            self.assertTrue(os.path.exists(service_file))
        finally:
            shutil.rmtree(temp_dir)

    def test_compile_file_with_traversal_output_file(self):
        """Test that path traversal in output_file is rejected."""
        temp_dir = tempfile.mkdtemp()
        try:
            kustomization = {
                "resources": ["deployment.yaml"],
            }
            with open(
                os.path.join(temp_dir, "kustomization.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(kustomization, f)

            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "test-deployment"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {"name": "test-container", "image": "nginx:latest"}
                            ]
                        }
                    }
                },
            }
            with open(
                os.path.join(temp_dir, "deployment.yaml"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(deployment, f)

            config = KapitanInputTypeKustomizeConfig(
                input_paths=[temp_dir],
                output_path=self.compile_path,
                output_file="../escape.yml",
            )

            with self.assertRaises(KustomizeTemplateError):
                self.kustomize.compile_file(config, temp_dir, self.compile_path)

            # Absolute path should also be rejected
            config_abs = KapitanInputTypeKustomizeConfig(
                input_paths=[temp_dir],
                output_path=self.compile_path,
                output_file="/tmp/escape.yml",
            )
            with self.assertRaises(KustomizeTemplateError):
                self.kustomize.compile_file(config_abs, temp_dir, self.compile_path)
        finally:
            shutil.rmtree(temp_dir)


class KustomizeConfigSchemaTest(unittest.TestCase):
    """Test Pydantic schema behavior for Kustomize config."""

    def test_output_file_accepted(self):
        """output_file should be accepted as a valid field."""
        config = KapitanInputTypeKustomizeConfig(
            input_paths=["./components/kustomize/multus"],
            output_path="manifests",
            output_file="install.yml",
        )
        self.assertEqual(config.output_file, "install.yml")

    def test_unknown_field_rejected(self):
        """Unknown fields should be rejected by extra='forbid'."""
        with self.assertRaises(ValidationError):
            KapitanInputTypeKustomizeConfig(
                input_paths=["./foo"],
                output_path="bar",
                unknown_field="value",
            )


if __name__ == "__main__":
    unittest.main()
