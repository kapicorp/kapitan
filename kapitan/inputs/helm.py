import logging
import os
import tempfile

from yaml import SafeDumper
import yaml

from kapitan.errors import HelmTemplateError
from kapitan.helm_cli import helm_cli
from kapitan.inputs.base import InputType, CompiledFile

logger = logging.getLogger(__name__)

HELM_DENIED_FLAGS = {
    "dry-run",
    "generate-name",
    "help",
    "output-dir",
    "show-only",
}


class Helm(InputType):
    def __init__(self, compile_path, search_paths, ref_controller, args):
        super().__init__("helm", compile_path, search_paths, ref_controller)

        self.helm_values_files = args.get("helm_values_files")
        self.helm_params = args.get("helm_params") or {}
        self.helm_path = args.get("helm_path")
        self.file_path = None

        self.helm_values_file = None
        if "helm_values" in args:
            """dump helm values into a yaml file whose path will be passed over to Go helm code"""
            _, self.helm_values_file = tempfile.mkstemp(".helm_values.yml", text=True)
            with open(self.helm_values_file, "w") as fp:
                SafeDumper.add_representer(
                    type(None),
                    lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:null', '')
                )
                yaml.safe_dump(args["helm_values"], fp, default_flow_style=False)

        self.kube_version = None
        if "kube_version" in args:
            logger.warning("passing kube_version is deprecated. Use api_versions helm flag instead.")
            self.kube_version = args["kube_version"]

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

        if self.file_path is not None:
            raise CompileError(
                "The same helm input was compiled with different input paths, which will give a wrong result."
                + f" The input paths found are: {self.file_path} and {file_path}."
                + f" The search paths were: {self.search_paths}."
            )
        self.file_path = file_path

        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.dirname(compile_path), exist_ok=True)
        # save the template output to temp dir first
        error_message = self.render_chart(
            chart_dir=file_path,
            output_path=temp_dir,
            helm_path=self.helm_path,
            helm_params=self.helm_params,
            helm_values_file=self.helm_values_file,
            helm_values_files=self.helm_values_files,
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

    def render_chart(
        self, chart_dir, output_path, helm_path, helm_params, helm_values_file, helm_values_files
    ):
        args = ["template"]

        name = helm_params.pop("name", None)
        output_file = helm_params.pop("output_file", None)

        flags = {"--include-crds": True, "--skip-tests": True}

        if self.kube_version:
            flags["--api-versions"] = self.kube_version

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

            flags[f"--{param}"] = value

        # 'release_name' used to be the "helm template" [NAME] parameter.
        # For backward compatibility, assume it is the '--release-name' flag only if its value is a bool.
        release_name = flags.get("--release-name")
        if release_name is not None and not isinstance(release_name, bool):
            logger.warning(
                "using 'release_name' to specify the output name is deprecated. Use 'name' instead"
            )
            del flags["--release-name"]
            # name is used in place of release_name if both are specified
            name = name or release_name

        for flag, value in flags.items():
            # boolean flag should be passed when present, and omitted when not specified
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            else:
                args.append(flag)
                args.append(str(value))

        """renders helm chart located at chart_dir, and stores the output to output_path"""
        if helm_values_file:
            args.append("--values")
            args.append(helm_values_file)

        if helm_values_files:
            for file_name in helm_values_files:
                args.append("--values")
                args.append(file_name)

        if not output_file:
            args.append("--output-dir")
            args.append(output_path)

        if "name_template" not in flags:
            args.append(name or "--generate-name")

        # uses absolute path to make sure helm interprets it as a
        # local dir and not a chart_name that it should download.
        args.append(chart_dir)

        if output_file:
            with open(os.path.join(output_path, output_file), "wb") as f:
                # can't be verbose when capturing stdout
                return helm_cli(helm_path, args, stdout=f)
        else:
            return helm_cli(helm_path, args, verbose="--debug" in flags)
