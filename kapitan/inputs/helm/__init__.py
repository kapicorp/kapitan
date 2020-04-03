import logging
import os
from kapitan.errors import HelmBindingUnavailableError, HelmTemplateError
from kapitan.inputs.base import InputType, CompiledFile
import tempfile
import platform
import yaml

try:
    from kapitan.inputs.helm.helm_binding import ffi
except ImportError:
    pass  # make this feature optional

logger = logging.getLogger(__name__)


class Helm(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("helm", compile_path, search_paths, ref_controller)
        self.helm_values_file = None
        self.helm_params = {}
        self.lib = self.initialise_binding()

    def initialise_binding(self):
        """returns the dl_opened library (.so file) if exists, otherwise None"""
        if platform.system() not in ("Linux", "Darwin"):  # TODO: later add binding for Mac
            return None
        # binding_path is kapitan/inputs/helm/libtemplate.so
        binding_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libtemplate.so")
        if not os.path.exists(binding_path):
            logger.debug("The helm binding does not exist at {}".format(binding_path))
            return None
        try:
            lib = ffi.dlopen(binding_path)
        except (NameError, OSError) as e:
            raise HelmBindingUnavailableError(
                "There was an error opening helm binding. " "Refer to the exception below:\n" + str(e)
            )
        return lib

    def dump_helm_values(self, helm_values):
        """dump helm values into a yaml file whose path will be passed over to Go helm code"""
        _, self.helm_values_file = tempfile.mkstemp(".helm_values.yml", text=True)
        with open(self.helm_values_file, "w") as fp:
            yaml.safe_dump(helm_values, fp)

    def set_helm_params(self, helm_params):
        self.helm_params = helm_params

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Render templates in file_path/templates and write to compile_path.
        file_path must be a directory containing helm chart.
        kwargs:
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled
        """
        if not self.lib:
            raise HelmBindingUnavailableError(
                "Helm binding is not supported for {}."
                "\nOr the binding does not exist.".format(platform.system())
            )

        reveal = kwargs.get("reveal", False)
        target_name = kwargs.get("target_name", None)

        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.dirname(compile_path), exist_ok=True)
        # save the template output to temp dir first
        error_message = self.render_chart(
            chart_dir=file_path,
            output_path=temp_dir,
            helm_values_file=self.helm_values_file,
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
                        item_path, self.ref_controller, mode="w", reveal=reveal, target_name=target_name
                    ) as fp:
                        yml_obj = list(yaml.safe_load_all(f))
                        fp.write_yaml(yml_obj)
                        logger.debug("Wrote file %s to %s", full_file_name, item_path)

        self.helm_values_file = None  # reset this
        self.helm_params = {}

    def default_output_type(self):
        return None

    def render_chart(self, chart_dir, output_path, **kwargs):
        """renders helm chart located at chart_dir, and stores the output to output_path"""
        if kwargs.get("helm_values_file", None):
            helm_values_file = ffi.new("char[]", kwargs["helm_values_file"].encode("ascii"))
        else:
            # the value in kwargs can be None
            helm_values_file = ffi.new("char[]", "".encode("ascii"))

        if kwargs.get("namespace", None):
            namespace = ffi.new("char[]", kwargs["namespace"].encode("ascii"))
        else:
            namespace = ffi.new("char[]", "default".encode("ascii"))

        if kwargs.get("release_name", None):
            release_name = ffi.new("char[]", kwargs["release_name"].encode("ascii"))
        else:
            release_name = ffi.new("char[]", "".encode("ascii"))

        if kwargs.get("name_template", None):
            name_template = ffi.new("char[]", kwargs["name_template"].encode("ascii"))
        else:
            name_template = ffi.new("char[]", "".encode("ascii"))

        char_dir_buf = ffi.new("char[]", chart_dir.encode("ascii"))
        output_path_buf = ffi.new("char[]", output_path.encode("ascii"))

        c_error_message = self.lib.renderChart(
            char_dir_buf, output_path_buf, helm_values_file, namespace, release_name, name_template
        )
        error_message = ffi.string(c_error_message)  # this creates a copy as bytes
        self.lib.free(c_error_message)  # free the char* returned by go
        return error_message.decode("utf-8")  # empty if no error
