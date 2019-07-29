import logging
import os
from kapitan.errors import HelmBindingUnavailableError, HelmTemplateError
from kapitan.inputs.base import InputType, CompiledFile
import tempfile
import yaml

try:
    from kapitan.inputs.helm.helm_binding import ffi
except ImportError:
    pass # make this feature optional

logger = logging.getLogger(__name__)


class Helm(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("helm", compile_path, search_paths, ref_controller)
        self.helm_values_file = None
        self.helm_params = {}

    def dump_helm_values(self, helm_values):
        """dump helm values into a yaml file whose path will be passed over to Go helm code"""
        _, self.helm_values_file = tempfile.mkstemp('.helm_values.yml', text=True)
        with open(self.helm_values_file, 'w') as fp:
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
        reveal = kwargs.get('reveal', False)
        target_name = kwargs.get('target_name', None)

        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.dirname(compile_path), exist_ok=True)
        # save the template output to temp dir first
        error_message = render_chart(chart_dir=file_path, output_path=temp_dir,
                                     helm_values_file=self.helm_values_file, **self.helm_params)
        if error_message:
            raise HelmTemplateError(error_message)

        walk_root_files = os.walk(temp_dir)
        for root, _, files in walk_root_files:
            for file in files:  # go through all the template files
                with open(os.path.join(root, file), 'r') as f:
                    item_path = os.path.join(compile_path, file)
                    with CompiledFile(item_path, self.ref_controller, mode="w", reveal=reveal, target_name=target_name) as fp:
                        fp.write(f.read())
                        logger.debug("Wrote file %s to %s", os.path.join(file_path, file), item_path)

        self.helm_values_file = None  # reset this
        self.helm_params = {}

    def default_output_type(self):
        return None


def render_chart(chart_dir, output_path, **kwargs):
    """renders helm chart located at chart_dir, and stores the output to output_path"""
    try:
        # lib is opened inside the function to allow multiprocessing
        lib = ffi.dlopen(os.path.join(os.path.dirname(os.path.abspath(__file__)), "libtemplate.so"))
    except NameError:
        raise HelmBindingUnavailableError("Helm binding is not available. Run 'make build_helm_binding' to create it")

    if kwargs.get('helm_values_file', None):
        helm_values_file = ffi.new("char[]", kwargs['helm_values_file'].encode('ascii'))
    else:
        # the value in kwargs can be None
        helm_values_file = ffi.new("char[]", "".encode('ascii'))

    if kwargs.get('namespace', None):
        namespace = ffi.new("char[]", kwargs['namespace'].encode('ascii'))
    else:
        namespace = ffi.new("char[]", 'default'.encode('ascii'))

    if kwargs.get('release_name', None):
        release_name = ffi.new("char[]", kwargs['release_name'].encode('ascii'))
    else:
        release_name = ffi.new("char[]", ''.encode('ascii'))

    if kwargs.get('name_template', None):
        name_template = ffi.new("char[]", kwargs['name_template'].encode('ascii'))
    else:
        name_template = ffi.new("char[]", ''.encode('ascii'))

    char_dir_buf = ffi.new("char[]", chart_dir.encode('ascii'))
    output_path_buf = ffi.new("char[]", output_path.encode('ascii'))

    c_error_message = lib.renderChart(char_dir_buf, output_path_buf,
                                      helm_values_file, namespace,
                                      release_name, name_template)
    error_message = ffi.string(c_error_message)  # this creates a copy as bytes
    lib.free(c_error_message)  # free the char* returned by go
    return error_message.decode("utf-8")  # empty if no error
