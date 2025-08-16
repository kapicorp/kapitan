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
        self.args = type("Args", (), {"kustomize_path": "kustomize"})
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
            with self.assertRaises(Exception):
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
            with open(output_file) as f:
                output = yaml.safe_load(f)
                self.assertEqual(
                    output["spec"]["template"]["spec"]["containers"][0]["image"],
                    "nginx:latest",
                )

        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
