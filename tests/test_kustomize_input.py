#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for Kustomize input type refactored for pytest."""

import os
from typing import Any, Dict

import pytest
import yaml

from kapitan.inputs.kustomize import Kustomize
from kapitan.inventory.model.input_types import KapitanInputTypeKustomizeConfig


@pytest.fixture
def kustomize_compiler(temp_dir):
    """Create a Kustomize compiler instance for testing."""
    compile_path = os.path.join(temp_dir, "compiled")
    os.makedirs(compile_path, exist_ok=True)
    search_paths = []
    ref_controller = None
    target_name = "test-target"
    args = type("Args", (), {"kustomize_path": "kustomize"})

    return Kustomize(
        compile_path,
        search_paths,
        ref_controller,
        target_name,
        args,
    )


class TestKustomizeInput:
    """Test cases for Kustomize input type."""

    def test_compile_file_with_patches(self, kustomize_compiler, temp_dir):
        """Test compiling a Kustomize overlay with patches."""
        # Create a directory for the test resources
        kustomize_dir = os.path.join(temp_dir, "kustomize_test")
        os.makedirs(kustomize_dir, exist_ok=True)

        # Create a basic kustomization.yaml
        kustomization = {
            "resources": ["deployment.yaml"],
            "namespace": "test-namespace",
        }
        with open(os.path.join(kustomize_dir, "kustomization.yaml"), "w") as f:
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
        with open(os.path.join(kustomize_dir, "deployment.yaml"), "w") as f:
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
            input_paths=[kustomize_dir],
            output_path=kustomize_compiler.compile_path,
        )

        # Compile the overlay
        kustomize_compiler.compile_file(config, kustomize_dir, kustomize_compiler.compile_path)

        # Verify the output
        output_file = os.path.join(kustomize_compiler.compile_path, "test-deployment-deployment.yaml")
        assert os.path.exists(output_file)

        with open(output_file, "r") as f:
            output = yaml.safe_load(f)
            assert output["spec"]["template"]["spec"]["containers"][0]["image"] == "nginx:1.19"

    def test_compile_file_with_namespace(self, kustomize_compiler, temp_dir):
        """Test compiling a Kustomize overlay with namespace."""
        # Create a directory for the test resources
        kustomize_dir = os.path.join(temp_dir, "kustomize_test")
        os.makedirs(kustomize_dir, exist_ok=True)

        # Create a basic kustomization.yaml
        kustomization = {
            "resources": ["deployment.yaml"],
        }
        with open(os.path.join(kustomize_dir, "kustomization.yaml"), "w") as f:
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
        with open(os.path.join(kustomize_dir, "deployment.yaml"), "w") as f:
            yaml.dump(deployment, f)

        # Create config
        config = KapitanInputTypeKustomizeConfig(
            namespace="test-namespace",
            input_paths=[kustomize_dir],
            output_path=kustomize_compiler.compile_path,
        )

        # Compile the overlay
        kustomize_compiler.compile_file(config, kustomize_dir, kustomize_compiler.compile_path)

        # Verify the output
        output_file = os.path.join(kustomize_compiler.compile_path, "test-deployment-deployment.yaml")
        assert os.path.exists(output_file)

        with open(output_file, "r") as f:
            output = yaml.safe_load(f)
            assert output["metadata"]["namespace"] == "test-namespace"

    def test_compile_file_with_invalid_input(self, kustomize_compiler, temp_dir):
        """Test compiling a Kustomize overlay with invalid input."""
        # Create a directory for the test resources
        kustomize_dir = os.path.join(temp_dir, "kustomize_test")
        os.makedirs(kustomize_dir, exist_ok=True)

        # Create an invalid kustomization.yaml
        kustomization = {
            "resources": ["nonexistent.yaml"],
        }
        with open(os.path.join(kustomize_dir, "kustomization.yaml"), "w") as f:
            yaml.dump(kustomization, f)

        # Create config
        config = KapitanInputTypeKustomizeConfig(
            namespace="test-namespace",
            input_paths=[kustomize_dir],
            output_path=kustomize_compiler.compile_path,
        )

        # Compile the overlay and expect an error
        with pytest.raises(Exception):
            kustomize_compiler.compile_file(config, kustomize_dir, kustomize_compiler.compile_path)

    def test_compile_file_with_invalid_patch(self, kustomize_compiler, temp_dir):
        """Test compiling a Kustomize overlay with invalid patch."""
        # Create a directory for the test resources
        kustomize_dir = os.path.join(temp_dir, "kustomize_test")
        os.makedirs(kustomize_dir, exist_ok=True)

        # Create a basic kustomization.yaml
        kustomization = {
            "resources": ["deployment.yaml"],
        }
        with open(os.path.join(kustomize_dir, "kustomization.yaml"), "w") as f:
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
        with open(os.path.join(kustomize_dir, "deployment.yaml"), "w") as f:
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
            input_paths=[kustomize_dir],
            output_path=kustomize_compiler.compile_path,
        )

        # Compile the overlay
        kustomize_compiler.compile_file(config, kustomize_dir, kustomize_compiler.compile_path)

        # Verify the output
        output_file = os.path.join(kustomize_compiler.compile_path, "test-deployment-deployment.yaml")
        assert os.path.exists(output_file)

        # Verify that the patch was not applied (image should still be nginx:latest)
        with open(output_file, "r") as f:
            output = yaml.safe_load(f)
            assert output["spec"]["template"]["spec"]["containers"][0]["image"] == "nginx:latest"
