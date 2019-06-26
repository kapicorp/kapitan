import os

try:
    from kapitan.inputs.helm._template import ffi
    lib = ffi.dlopen(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "libtemplate.so"))
except ImportError:
    pass # make this feature optional


def render_chart(chart_dir, output_path):
    """renders helm chart located at chart_dir, and stores the output to output_path"""
    char_dir_buf = ffi.new("char[]", chart_dir.encode('ascii'))
    output_path_buf = ffi.new("char[]", output_path.encode('ascii'))
    c_error_message = lib.renderChart(char_dir_buf, output_path_buf)
    error_message = ffi.string(c_error_message) # this creates a copy as bytes
    lib.free(c_error_message) # free the char* returned by go
    return error_message.decode("utf-8")  # empty if no error
