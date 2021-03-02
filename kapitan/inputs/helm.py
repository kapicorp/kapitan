import logging
import os
import tempfile

import yaml
from kapitan.errors import HelmTemplateError
from kapitan.helm_cli import helm_cli
from kapitan.inputs.base import InputType, CompiledFile

logger = logging.getLogger(__name__)


class Helm(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("helm", compile_path, search_paths, ref_controller)
        self.helm_values_file = None
        self.helm_values_files = []
        self.helm_params = {}
        self.kube_version = ""

    def dump_helm_values(self, helm_values):
        """dump helm values into a yaml file whose path will be passed over to Go helm code"""
        _, self.helm_values_file = tempfile.mkstemp(".helm_values.yml", text=True)
        with open(self.helm_values_file, "w") as fp:
            yaml.safe_dump(helm_values, fp)

    def set_helm_values_files(self, helm_values_files):
        self.helm_values_files = helm_values_files

    def set_helm_params(self, helm_params):
        self.helm_params = helm_params

    def set_kube_version(self, kube_version):
        self.kube_version = kube_version

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Render templates in file_path/templates and write to compile_path.
        file_path must be a directory containing helm chart.
        kwargs:
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled
        """
        reveal = kwargs.get("reveal", False)
        target_name = kwargs.get("target_name", None)

        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.dirname(compile_path), exist_ok=True)
        # save the template output to temp dir first
        error_message = self.render_chart(
            chart_dir=file_path,
            output_path=temp_dir,
            helm_values_file=self.helm_values_file,
            helm_values_files=self.helm_values_files,
            **self.helm_params,
        )
        if error_message:
            raise HelmTemplateError(error_message)

        walk_root_files = os.walk(temp_dir)
        for current_dir, _, files in walk_root_files:
            for file in files:  # go through all the template files
                rel_dir = os.path.relpath(current_dir, temp_dir)
                rel_file_name = os.path.join(rel_dir, file)
                full_file_name = os.path.join(current_dir, file)
                with open(full_file_name, "r") as f:
                    item_path = os.path.join(compile_path, rel_file_name)
                    os.makedirs(os.path.dirname(item_path), exist_ok=True)
                    with CompiledFile(
                        item_path,
                        self.ref_controller,
                        mode="w",
                        reveal=reveal,
                        target_name=target_name,
                    ) as fp:
                        yml_obj = list(yaml.safe_load_all(f))
                        fp.write_yaml(yml_obj)
                        logger.debug("Wrote file %s to %s", full_file_name, item_path)

        self.helm_values_file = None  # reset this
        self.helm_params = {}
        self.helm_values_files = []

    def default_output_type(self):
        return None

    def render_chart(self, chart_dir, output_path, **kwargs):
        args = ["template"]
        """renders helm chart located at chart_dir, and stores the output to output_path"""
        if kwargs.get("helm_values_files", []):
            for file_name in kwargs["helm_values_files"]:
                args.append("-f")
                args.append(file_name)

        if kwargs.get("helm_values_file", None):
            args.append("-f")
            args.append(kwargs["helm_values_file"])

        if kwargs.get("namespace", None):
            args.append("-n")
            args.append(kwargs["namespace"])

        args.append("--output-dir")
        args.append(output_path)

        if self.kube_version:
            args.append("--api-versions")
            args.append(self.kube_version)

        if kwargs.get("validate", False):
            args.append("--validate")

        if kwargs.get("name_template", None):
            args.append("--name-template")
            args.append(kwargs["name_template"])
        else:
            args.append(kwargs.get("release_name", "--generate-name"))

        # uses absolute path to make sure helm interpret it as a
        # local dir and not a chart_name that it should download.
        args.append(os.path.abspath(chart_dir))

        return helm_cli(args)
