def get_suffix(name: str):
    return name.split("-")[-1]


def get_substr(name: str, substr: int = -2):
    return name.split("-")[substr]


def helm_dep(name: str, source: str):
    """kapitan template for a helm chart dependency"""
    return {
        "type": "helm",
        "output_path": f"charts/${{{name}.chart_name}}/${{{name}.chart_version}}/${{{name}.application_version}}",
        "source": source,
        "version": f"${{{name}.chart_version}}",
        "chart_name": f"${{{name}.chart_name}}",
    }


def helm_input(name: str, output_file: str = ""):
    """kapitan template for a helm input type configuration"""

    if not output_file:
        output_file = name
    return {
        "input_type": "helm",
        "input_paths": [
            f"charts/${{{name}.chart_name}}/${{{name}.chart_version}}/${{{name}.application_version}}"
        ],
        "output_path": f"k8s/${{{name}.namespace}}",
        "helm_params": {
            "namespace": f"${{{name}.namespace}}",
            "name": f"${{{name}.chart_name}}",
            "output_file": f"{output_file}.yml",
        },
        "helm_values": f"\\${{{name}.helm_values}}",  # \\ used for delaying the resolving of helm values
    }


def pass_resolvers():
    return {
        "get_suffix": get_suffix,
        "get_substr": get_substr,
        "helm_dep": helm_dep,
        "helm_input": helm_input,
    }
