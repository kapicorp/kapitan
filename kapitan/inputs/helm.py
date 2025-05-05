#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Helm templating tool implementation for Kapitan.

This module provides a Helm implementation for the Kapitan templating system.
It allows rendering Helm charts and integrating them into Kapitan's compilation process.
"""

import logging
import os
import shutil
import tempfile
from typing import Any, Dict, Optional, Tuple

import yaml

from kapitan.errors import HelmTemplateError
from kapitan.helm_cli import helm_cli
from kapitan.inputs.base import InputType
from kapitan.inputs.kadet import BaseModel, BaseObj
from kapitan.inventory.model.input_types import KapitanInputTypeHelmConfig

logger = logging.getLogger(__name__)

# Set of Helm flags that are not allowed to be used
HELM_DENIED_FLAGS = {
    "dry-run",
    "generate-name",
    "help",
    "output-dir",
    "show-only",
}

# Default flags to be used with Helm
HELM_DEFAULT_FLAGS = {"--include-crds": True, "--skip-tests": True}


def write_helm_values_file(helm_values: Dict[str, Any]) -> str:
    """Dump helm values into a temporary YAML file.

    This function creates a temporary YAML file containing the Helm values
    that will be used during chart rendering.

    Args:
        helm_values: A dictionary containing helm values to be written

    Returns:
        str: The path to the temporary YAML file
    """
    _, helm_values_file = tempfile.mkstemp(".helm_values.yml", text=True)
    with open(helm_values_file, "w") as fp:
        yaml.safe_dump(helm_values, fp)

    return helm_values_file


class Helm(InputType):
    """Helm templating tool implementation.

    This class implements the InputType interface for Helm.
    It handles rendering of Helm charts using the helm CLI.

    Configuration options:
        helm_path: Path to the helm binary (default: 'helm')
        helm_values: Dictionary of values to pass to the chart
        helm_values_files: List of paths to values files
        helm_params: Dictionary of additional helm parameters
        kube_version: Kubernetes version for API validation
    """

    def __init__(self, compile_path: str, search_paths: list, ref_controller, target_name: str, args):
        """Initialize the Helm templating tool.

        Args:
            compile_path: Base path for compiled output
            search_paths: List of paths to search for input files
            ref_controller: Reference controller for handling refs
            target_name: Name of the target being compiled
            args: Additional arguments passed to the tool
        """
        super().__init__(compile_path, search_paths, ref_controller, target_name, args)
        self.helm_path = args.helm_path if hasattr(args, "helm_path") else "helm"

    def compile_file(self, config: KapitanInputTypeHelmConfig, input_path: str, compile_path: str) -> None:
        """Compile a Helm chart.

        This method:
        1. Prepares Helm values and parameters
        2. Creates a temporary directory for output
        3. Renders the chart using helm template
        4. Writes the output to the compile path

        Args:
            config: Configuration object containing Helm-specific settings
            input_path: Path to the Helm chart
            compile_path: Path where rendered output should be written

        Raises:
            HelmTemplateError: If helm template fails
        """
        helm_values_files = config.helm_values_files
        helm_params = config.helm_params
        helm_path = config.helm_path

        # Create temporary values file if values are provided
        helm_values_file = None
        if config.helm_values:
            helm_values_file = write_helm_values_file(config.helm_values)

        # Prepare Helm flags
        helm_flags = dict(HELM_DEFAULT_FLAGS)
        if config.kube_version:
            helm_flags["--api-versions"] = config.kube_version

        # Create temporary directory for output
        temp_dir = tempfile.mkdtemp()

        # Render the chart
        _, error_message = self.render_chart(
            chart_dir=input_path,
            output_path=temp_dir,
            helm_path=helm_path,
            helm_params=helm_params,
            helm_values_file=helm_values_file,
            helm_values_files=helm_values_files,
            helm_flags=helm_flags,
        )

        if error_message:
            raise HelmTemplateError(error_message)

        # Copy rendered files to compile path
        for root, _, files in os.walk(temp_dir):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, temp_dir)
                dst_path = os.path.join(compile_path, rel_path)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

    def render_chart(
        self,
        chart_dir: str,
        output_path: str,
        helm_path: str,
        helm_params: Dict[str, Any],
        helm_values_file: Optional[str],
        helm_values_files: Optional[list],
        helm_flags: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Optional[str]]:
        """Render a Helm chart using the helm CLI.

        This is a helper method that handles the actual helm template command execution.
        It validates parameters, builds the command, and executes it.

        Args:
            chart_dir: Path to the Helm chart directory
            output_path: Path to write rendered chart
            helm_path: Path to the helm binary
            helm_params: Dictionary of Helm parameters
            helm_values_file: Path to a values file
            helm_values_files: List of paths to values files
            helm_flags: Dictionary of additional Helm flags

        Returns:
            Tuple[str, Optional[str]]: (output, error_message)

        Raises:
            ValueError: If invalid parameters are provided
        """
        args = ["template"]
        helm_flags = helm_flags or HELM_DEFAULT_FLAGS

        # Extract special parameters
        name = helm_params.pop("name", None)
        output_file = helm_params.pop("output_file", None)

        # Validate and process parameters
        self._validate_helm_params(helm_params)
        self._process_helm_params(helm_params, helm_flags)

        # Handle release name
        self._handle_release_name(name, helm_flags)

        # Build the command
        self._build_helm_command(
            args,
            helm_flags,
            helm_values_file,
            helm_values_files,
            output_path,
            output_file,
            name,
            chart_dir,
        )

        # Execute the command
        return self._execute_helm_command(helm_path, args, output_path, output_file, helm_flags)

    def _validate_helm_params(self, helm_params: Dict[str, Any]) -> None:
        """Validate Helm parameters.

        Args:
            helm_params: Dictionary of Helm parameters

        Raises:
            ValueError: If parameters are invalid
        """
        for param, value in helm_params.items():
            if len(param) == 1:
                raise ValueError(f"invalid helm flag: '{param}'. helm_params supports only long flag names")

            if "-" in param:
                raise ValueError(f"helm flag names must use '_' and not '-': {param}")

            if param in ("set", "set-file", "set-string"):
                raise ValueError(
                    f"helm '{param}' flag is not supported. Use 'helm_values' to specify template values"
                )

            if param == "values":
                raise ValueError(
                    f"helm '{param}' flag is not supported. Use 'helm_values_files' to specify template values files"
                )

            if param in HELM_DENIED_FLAGS:
                raise ValueError(f"helm flag '{param}' is not supported.")

    def _process_helm_params(self, helm_params: Dict[str, Any], helm_flags: Dict[str, Any]) -> None:
        """Process Helm parameters into flags.

        Args:
            helm_params: Dictionary of Helm parameters
            helm_flags: Dictionary to store processed flags
        """
        for param, value in helm_params.items():
            param = param.replace("_", "-")
            helm_flags[f"--{param}"] = value

    def _handle_release_name(self, name: Optional[str], helm_flags: Dict[str, Any]) -> None:
        """Handle release name parameter.

        Args:
            name: Release name
            helm_flags: Dictionary of Helm flags
        """
        release_name = helm_flags.get("--release-name")
        if release_name is not None and not isinstance(release_name, bool):
            logger.warning(
                "using 'release_name' to specify the output name is deprecated. Use 'name' instead"
            )
            del helm_flags["--release-name"]
            name = name or release_name

    def _build_helm_command(
        self,
        args: list,
        helm_flags: Dict[str, Any],
        helm_values_file: Optional[str],
        helm_values_files: Optional[list],
        output_path: str,
        output_file: Optional[str],
        name: Optional[str],
        chart_dir: str,
    ) -> None:
        """Build the Helm command.

        Args:
            args: List to store command arguments
            helm_flags: Dictionary of Helm flags
            helm_values_file: Path to a values file
            helm_values_files: List of paths to values files
            output_path: Path to write output
            output_file: Specific output file
            name: Release name
            chart_dir: Path to chart directory
        """
        # Add flags
        for flag, value in helm_flags.items():
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            else:
                args.append(flag)
                args.append(str(value))

        # Add values files
        if helm_values_file:
            args.extend(["--values", helm_values_file])
        if helm_values_files:
            for file_name in helm_values_files:
                args.extend(["--values", file_name])

        # Set output directory
        if not output_file and output_path not in (None, "-"):
            args.extend(["--output-dir", output_path])

        # Add name or generate-name
        if "name_template" not in helm_flags:
            args.append(name or "--generate-name")

        # Add chart directory
        args.append(chart_dir)

    def _execute_helm_command(
        self,
        helm_path: str,
        args: list,
        output_path: str,
        output_file: Optional[str],
        helm_flags: Dict[str, Any],
    ) -> Tuple[str, Optional[str]]:
        """Execute the Helm command.

        Args:
            helm_path: Path to helm binary
            args: Command arguments
            output_path: Path to write output
            output_file: Specific output file
            helm_flags: Dictionary of Helm flags

        Returns:
            Tuple[str, Optional[str]]: (output, error_message)
        """
        if output_path == "-":
            _, helm_output = tempfile.mkstemp(".helm_output.yml", text=True)
            with open(helm_output, "w+") as f:
                error_message = helm_cli(helm_path, args, stdout=f)
                f.seek(0)
                return (f.read(), error_message)

        if output_file:
            with open(os.path.join(output_path, output_file), "wb") as f:
                error_message = helm_cli(helm_path, args, stdout=f)
                return ("", error_message)
        else:
            error_message = helm_cli(helm_path, args, verbose="--debug" in helm_flags)
            return ("", error_message)


class HelmChart(BaseModel):
    """Represents a Helm chart for programmatic use.

    This class provides a programmatic interface to Helm charts, allowing them
    to be rendered and manipulated in Python code. It stores the rendered objects
    in self.root for further processing.

    Example:
        chart = HelmChart(
            chart_dir="charts/my-chart",
            helm_values={"replicas": 3},
            helm_params={"name": "my-release"}
        )
        chart.new()  # Renders the chart
        print(chart.root)  # Access rendered objects
    """

    chart_dir: str
    helm_params: Dict[str, Any] = {}
    helm_values: Dict[str, Any] = {}
    helm_path: Optional[str] = None

    def new(self) -> None:
        """Render the chart and store objects in self.root.

        This method:
        1. Loads the chart using load_chart()
        2. Processes each object
        3. Stores them in self.root with unique keys

        The keys are constructed as: {name}-{kind} where both are lowercase
        and special characters are replaced with hyphens.
        """
        for obj in self.load_chart():
            if obj:
                self.root[f"{obj['metadata']['name'].lower()}-{obj['kind'].lower().replace(':','-')}"] = (
                    BaseObj.from_dict(obj)
                )

    def load_chart(self) -> list:
        """Load and render the Helm chart.

        Returns:
            list: List of rendered Kubernetes objects

        Raises:
            HelmTemplateError: If chart rendering fails
        """
        # Create a Helm instance to handle the rendering
        helm = Helm(
            compile_path="",  # Not needed for our use case
            search_paths=[],  # Not needed for our use case
            ref_controller=None,  # Not needed for our use case
            target_name="",  # Not needed for our use case
            args=None,  # Not needed for our use case
        )

        # Create temporary values file if values are provided
        helm_values_file = None
        if self.helm_values:
            helm_values_file = write_helm_values_file(self.helm_values)

        # Prepare Helm flags
        helm_flags = dict(HELM_DEFAULT_FLAGS)

        # Render the chart
        output, error_message = helm.render_chart(
            chart_dir=self.chart_dir,
            output_path="-",  # Output to stdout
            helm_path=self.helm_path or "helm",
            helm_params=self.helm_params,
            helm_values_file=helm_values_file,
            helm_values_files=None,
            helm_flags=helm_flags,
        )

        if error_message:
            raise HelmTemplateError(error_message)

        return list(yaml.safe_load_all(output))
