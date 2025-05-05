#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Kustomize implementation for Kapitan.

This module provides a Kustomize implementation for rendering overlays.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import yaml

from kapitan.errors import KustomizeTemplateError
from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import KapitanInputTypeKustomizeConfig

logger = logging.getLogger(__name__)


class Kustomize(InputType):
    """Kustomize implementation.

    This class implements the InputType interface for Kustomize.
    It handles rendering of Kustomize overlays using the kustomize CLI.

    Configuration options:
        kustomize_path: Path to the kustomize binary (default: 'kustomize')
        namespace: Namespace to set in the rendered manifests
        patches: Dictionary of patches to apply
        patches_strategic: Dictionary of strategic merge patches to apply
        patches_json: Dictionary of JSON patches to apply
    """

    def __init__(self, compile_path: str, search_paths: list, ref_controller, target_name: str, args):
        """Initialize the Kustomize implementation.

        Args:
            compile_path: Base path for compiled output
            search_paths: List of paths to search for input files
            ref_controller: Reference controller for handling refs
            target_name: Name of the target being compiled
            args: Additional arguments passed to the tool
        """
        super().__init__(compile_path, search_paths, ref_controller, target_name, args)
        self.kustomize_path = args.kustomize_path if hasattr(args, "kustomize_path") else "kustomize"

    def compile_file(
        self, config: KapitanInputTypeKustomizeConfig, input_path: str, compile_path: str
    ) -> None:
        """Compile a Kustomize overlay.

        This method:
        1. Prepares the kustomize command
        2. Creates and applies patches if specified
        3. Renders the overlay
        4. Writes the output to the compile path

        Args:
            config: Configuration object containing Kustomize-specific settings
            input_path: Path to the Kustomize overlay
            compile_path: Path where rendered output should be written

        Raises:
            KustomizeTemplateError: If kustomize build fails
        """
        try:
            # Create a temporary directory for our kustomization
            temp_dir = tempfile.mkdtemp()
            kustomization_path = os.path.join(temp_dir, "kustomization.yaml")

            # Get the absolute path to the input directory
            abs_input_path = os.path.abspath(input_path)
            if not os.path.isdir(abs_input_path):
                raise KustomizeTemplateError(
                    f"Input path {input_path} must be a directory containing a kustomization.yaml file"
                )

            # Copy the input directory to the temporary directory
            input_dir_name = os.path.basename(abs_input_path)
            temp_input_dir = os.path.join(temp_dir, input_dir_name)
            shutil.copytree(abs_input_path, temp_input_dir)

            # Read the original kustomization.yaml if it exists
            original_kustomization = {}
            original_kustomization_path = os.path.join(temp_input_dir, "kustomization.yaml")
            if os.path.exists(original_kustomization_path):
                with open(original_kustomization_path, "r") as f:
                    original_kustomization = yaml.safe_load(f) or {}

            # Create our kustomization with patches
            kustomization = {
                "resources": [input_dir_name],
                "namespace": config.namespace or original_kustomization.get("namespace", ""),
            }

            # Add patches if specified
            if config.patches:
                kustomization["patches"] = []
                for name, patch in config.patches.items():
                    patch_file = os.path.join(temp_dir, f"{name}.yaml")
                    with open(patch_file, "w") as f:
                        yaml.dump(patch["patch"], f, default_flow_style=False)
                    kustomization["patches"].append(
                        {"path": os.path.basename(patch_file), "target": patch["target"]}
                    )

            # Write the kustomization file
            with open(kustomization_path, "w") as f:
                yaml.dump(kustomization, f, default_flow_style=False)

            # Build the kustomize command
            cmd = [self.kustomize_path, "build", temp_dir]

            # Create temporary directory for output
            output_dir = tempfile.mkdtemp()
            output_file = os.path.join(output_dir, "output.yaml")

            # Run kustomize build
            with open(output_file, "w") as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    raise KustomizeTemplateError(f"Kustomize build failed: {result.stderr}")

            # Read and process the output
            with open(output_file, "r") as f:
                for doc in yaml.safe_load_all(f):
                    if doc:
                        # Generate a unique filename based on kind and name
                        kind = doc.get("kind", "").lower()
                        name = doc.get("metadata", {}).get("name", "").lower()
                        filename = f"{name}-{kind}.yaml" if name and kind else "output.yaml"

                        # Write the document to the output file
                        output_path = os.path.join(compile_path, filename)
                        with open(output_path, "w") as out:
                            yaml.dump(doc, out, default_flow_style=False)

        except Exception as e:
            raise KustomizeTemplateError(f"Failed to compile Kustomize overlay: {str(e)}")
