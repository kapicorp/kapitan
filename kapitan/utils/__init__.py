"""Utility helpers exposed via the public ``kapitan.utils`` namespace."""

from importlib import import_module


_EXPORTS = {
    "PrettyDumper": "kapitan.utils.yaml",
    "SafeCopyError": "kapitan.utils.filesystem",
    "StrEnum": "kapitan.utils.compat",
    "YamlLoader": "kapitan.utils.compat",
    "check_version": "kapitan.utils.cli",
    "compare_versions": "kapitan.utils.cli",
    "copy_tree": "kapitan.utils.filesystem",
    "deep_get": "kapitan.utils.data",
    "dictionary_hash": "kapitan.utils.hashing",
    "directory_hash": "kapitan.utils.hashing",
    "dot_kapitan_config": "kapitan.utils.cli",
    "fatal_error": "kapitan.utils.cli",
    "file_mode": "kapitan.utils.filesystem",
    "flatten_dict": "kapitan.utils.data",
    "force_copy_file": "kapitan.utils.filesystem",
    "from_dot_kapitan": "kapitan.utils.cli",
    "get_entropy": "kapitan.utils.hashing",
    "list_all_paths": "kapitan.utils.filesystem",
    "make_request": "kapitan.utils.network",
    "multiline_str_presenter": "kapitan.utils.yaml",
    "normalise_join_path": "kapitan.utils.filesystem",
    "null_presenter": "kapitan.utils.yaml",
    "prune_empty": "kapitan.utils.data",
    "render_jinja2": "kapitan.utils.jinja",
    "render_jinja2_file": "kapitan.utils.jinja",
    "render_jinja2_template": "kapitan.utils.jinja",
    "safe_copy_file": "kapitan.utils.filesystem",
    "safe_copy_tree": "kapitan.utils.filesystem",
    "search_target_token_paths": "kapitan.utils.search",
    "searchvar": "kapitan.utils.search",
    "sha256_string": "kapitan.utils.hashing",
    "termcolor": "kapitan.utils.cli",
    "unpack_downloaded_file": "kapitan.utils.filesystem",
    "with_temp_dir": "kapitan.utils.filesystem",
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name):
    try:
        module_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(list(globals()) + __all__)
