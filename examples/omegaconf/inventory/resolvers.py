import os


def double(x: int):
    """Multiply a number by two."""
    return x * 2


def concat(a: str, b: str):
    """Concatenate two strings."""
    return a + b


def env_or_default(name: str, default: str):
    """Read an environment variable with a safe deterministic default."""
    return os.environ.get(name, default)


def get_suffix(name: str):
    """Extract the last part of a hyphen-separated string."""
    return name.split("-")[-1]


def get_substr(name: str, substr: int = -2):
    """Extract a specific part of a hyphen-separated string by index."""
    return name.split("-")[substr]


def upper(content: str):
    """Convert string to uppercase."""
    return content.upper()


def capitalize(input_str: str):
    """Capitalize hyphenated words (camelCase style)."""
    parts = input_str.split("-")
    return parts[0] + "".join([x.capitalize() for x in parts[1:]])


def with_root(*args, _root_):
    """Demonstrate _root_ context access by building a path from target_name."""
    target_name = _root_.target_name
    return f"{target_name}/" + "/".join(args)


def pass_resolvers():
    return {
        "double": double,
        "concat": concat,
        "env_or_default": env_or_default,
        "get_suffix": get_suffix,
        "get_substr": get_substr,
        "upper": upper,
        "capitalize": capitalize,
        "with_root": with_root,
    }
