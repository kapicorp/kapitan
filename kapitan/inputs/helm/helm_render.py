import os
from _template import ffi

lib = ffi.dlopen(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "libtemplate.so"))


def render_chart(chart_dir, output_path):
    """renders helm chart located at chart_dir, and stores the output to output_path"""
    char_dir_buf = ffi.new("char[]", chart_dir.encode('ascii'))
    output_path_buf = ffi.new("char[]", output_path.encode('ascii'))
    lib.renderChart(char_dir_buf, output_path_buf)


def main():
    # TODO: this is here for now to test the code
    chart_dir = "chart/acs-engine-autoscaler"
    output_path = "test"
    render_chart(chart_dir, output_path)


if __name__ == '__main__':
    main()
