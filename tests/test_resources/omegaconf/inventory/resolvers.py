def get_suffix(name: str):
    """Extract the last part of a hyphen-separated string."""
    return name.split("-")[-1]


def get_substr(name: str, substr: int = -2):
    """Extract a specific part of a hyphen-separated string by index."""
    return name.split("-")[substr]


def mul(a: int, b: int):
    """Multiply two numbers."""
    return a * b


def upper(content: str):
    """Convert string to uppercase."""
    return content.upper()


def capitalize(input_str: str):
    """Capitalize hyphenated words (camelCase style)."""
    parts = input_str.split("-")
    return parts[0] + "".join([x.capitalize() for x in parts[1:]])


def escape(content: str):
    """Escape content with KAPITAN_LITERAL markers."""
    return f"__KAPITAN_LITERAL__{content}__KAPITAN_LITERAL_END__"


def vaultkvref(*args, _root_):
    """Generate a vault KV reference using _root_ context access."""
    target_name = _root_.target_name
    path = f"{target_name}/" + "/".join(args)
    mount = "ops_kv"
    vaultpath = "kapitan-test/" + "/".join(args[:-1])
    generate = "||random:str:16"

    value = "?{vaultkv:" + f"{path}:{mount}:{vaultpath}:{args[-1]}" + generate + "}"
    return value


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
        "mul": mul,
        "upper": upper,
        "capitalize": capitalize,
        "escape": escape,
        "vaultkv": vaultkvref,
        "helm_dep": helm_dep,
        "helm_input": helm_input,
    }
