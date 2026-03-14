"""YAML dumping utility helpers."""

import functools

import yaml

from kapitan import cached


class PrettyDumper(yaml.SafeDumper):
    """
    Increase the indent of nested lists when dumping YAML.
    """

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

    @classmethod
    def get_dumper_for_style(cls, style_selection="double-quotes"):
        cls.add_representer(
            str,
            functools.partial(multiline_str_presenter, style_selection=style_selection),
        )
        return cls


def multiline_str_presenter(dumper, data, style_selection="double-quotes"):
    """
    Configure yaml for dumping multiline strings with the given style.
    """
    supported_styles = {"literal": "|", "folded": ">", "double-quotes": '"'}
    style = supported_styles.get(style_selection)

    if data.count("\n") > 0:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def null_presenter(dumper, data):
    """Configure yaml for omitting a value from a null datatype."""
    flag_value = False
    if hasattr(cached.args, "yaml_dump_null_as_empty"):
        flag_value = cached.args.yaml_dump_null_as_empty

    if flag_value:
        return dumper.represent_scalar("tag:yaml.org,2002:null", "")
    return dumper.represent_scalar("tag:yaml.org,2002:null", "null")


PrettyDumper.add_representer(type(None), null_presenter)
