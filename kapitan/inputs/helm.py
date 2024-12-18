#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import tempfile

import yaml

from kapitan.errors import HelmTemplateError
from kapitan.helm_cli import helm_cli
from kapitan.inputs.base import InputType
from kapitan.inputs.kadet import BaseModel, BaseObj
from kapitan.inventory.model.input_types import KapitanInputTypeHelmConfig

logger = logging.getLogger(__name__)

HELM_DENIED_FLAGS = {
    "dry-run",
    "generate-name",
    "help",
    "output-dir",
    "show-only",
}

HELM_DEFAULT_FLAGS = {"--include-crds": True, "--skip-tests": True}


class Helm(InputType):
    def compile_file(self, config: KapitanInputTypeHelmConfig, input_path, compile_path):
        """Render templates in input_path/templates and write to compile_path.
        input_path must be a directory containing a helm chart.

        kwargs:
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled

        Raises:
            HelmTemplateError: if helm template fails

        """
        helm_values_files = config.helm_values_files
        helm_params = config.helm_params
        helm_path = config.helm_path

        helm_values_file = None
        if config.helm_values:
            helm_values_file = write_helm_values_file(config.helm_values)

        helm_flags = dict(HELM_DEFAULT_FLAGS)
        # add to flags if set
        if config.kube_version:
            helm_flags["--api-versions"] = config.kube_version

        temp_dir = tempfile.mkdtemp()
        # save the template output to temp dir first
        _, error_message = render_chart(
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
        # Iterate over all files in the temporary directory

        walk_root_files = os.walk(temp_dir)
        for current_dir, _, files in walk_root_files:
            for file in files:  # go through all the template files
                rel_dir = os.path.relpath(current_dir, temp_dir)
                rel_file_name = os.path.join(rel_dir, file)
                full_file_name = os.path.join(current_dir, file)
                # Open each file and write its content to the compilation path
                with open(full_file_name, "r", encoding="utf-8") as f:
                    file_path = os.path.join(compile_path, rel_file_name)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    item_value = list(yaml.safe_load_all(f))
                    self.to_file(config, file_path, item_value)

    def render_chart(self, *args, **kwargs):
        return render_chart(*args, **kwargs)


def render_chart(
    chart_dir,
    output_path,
    helm_path,
    helm_params,
    helm_values_file,
    helm_values_files,
    helm_flags=None,
):
    """
    Renders helm chart located at chart_dir.

    Args:
        output_path: path to write rendered chart. If '-', returns rendered chart as string.

    Returns:
        tuple: (output, error_message)
    """
    args = ["template"]

    name = helm_params.pop("name", None)
    output_file = helm_params.pop("output_file", None)

    if helm_flags is None:
        helm_flags = HELM_DEFAULT_FLAGS

    # Validate and process helm parameters
    for param, value in helm_params.items():
        if len(param) == 1:
            raise ValueError(f"invalid helm flag: '{param}'. helm_params supports only long flag names")

        if "-" in param:
            raise ValueError(f"helm flag names must use '_' and not '-': {param}")

        param = param.replace("_", "-")

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

        # Set helm flags
        helm_flags[f"--{param}"] = value

    # 'release_name' used to be the "helm template" [NAME] parameter.
    # For backward compatibility, assume it is the '--release-name' flag only if its value is a bool.
    release_name = helm_flags.get("--release-name")
    if release_name is not None and not isinstance(release_name, bool):
        logger.warning("using 'release_name' to specify the output name is deprecated. Use 'name' instead")
        del helm_flags["--release-name"]
        # name is used in place of release_name if both are specified
        name = name or release_name

    # Add flags to args list
    for flag, value in helm_flags.items():
        # boolean flag should be passed when present, and omitted when not specified
        if isinstance(value, bool):
            if value:
                args.append(flag)
        else:
            args.append(flag)
            args.append(str(value))

    # Add values files to args list
    if helm_values_file:
        args.append("--values")
        args.append(helm_values_file)

    if helm_values_files:
        for file_name in helm_values_files:
            args.append("--values")
            args.append(file_name)

    # Set output directory
    if not output_file and output_path not in (None, "-"):
        args.append("--output-dir")
        args.append(output_path)

    if "name_template" not in helm_flags:
        args.append(name or "--generate-name")

    # Add chart directory to args list
    # uses absolute path to make sure helm interprets it as a
    # local dir and not a chart_name that it should download.
    args.append(chart_dir)

    # If output_path is '-', output is a string with rendered chart
    if output_path == "-":
        _, helm_output = tempfile.mkstemp(".helm_output.yml", text=True)
        with open(helm_output, "w+") as f:
            error_message = helm_cli(helm_path, args, stdout=f)
            f.seek(0)
            return (f.read(), error_message)

    if output_file:
        with open(os.path.join(output_path, output_file), "wb") as f:
            # can't be verbose when capturing stdout
            error_message = helm_cli(helm_path, args, stdout=f)
            return ("", error_message)
    else:
        error_message = helm_cli(helm_path, args, verbose="--debug" in helm_flags)
        return ("", error_message)


def write_helm_values_file(helm_values: dict):
    """Dump helm values into a temporary YAML file.

    Args:
        helm_values: A dictionary containing helm values.

    Returns:
        str: The path to the temporary YAML file.
    """
    _, helm_values_file = tempfile.mkstemp(".helm_values.yml", text=True)
    with open(helm_values_file, "w") as fp:
        yaml.safe_dump(helm_values, fp)

    return helm_values_file


class HelmChart(BaseModel):
    """
    Represents a Helm chart. Renders the chart and stores the rendered objects in self.root.

    Args:
        chart_dir: Path to the Helm chart directory.

    Raises:
        HelmTemplateError: if helm template fails
    """

    chart_dir: str
    helm_params: dict = {}
    helm_values: dict = {}
    helm_path: str = None

    # Load and process the Helm chart
    def new(self):
        for obj in self.load_chart():
            self.root[f"{obj['metadata']['name'].lower()}-{obj['kind'].lower().replace(':','-')}"] = (
                BaseObj.from_dict(obj)
            )

    def load_chart(self):
        helm_values_file = None
        if self.helm_values != {}:
            helm_values_file = write_helm_values_file(self.helm_values)
        output, error_message = render_chart(
            self.chart_dir, "-", self.helm_path, self.helm_params, helm_values_file, None
        )
        if error_message:
            raise HelmTemplateError(error_message)

        return yaml.safe_load_all(output)
