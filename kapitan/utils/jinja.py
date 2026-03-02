"""Jinja rendering utility helpers."""

import os
import sys
import traceback
from functools import lru_cache

import jinja2

from kapitan import defaults
from kapitan.errors import CompileError
from kapitan.jinja2_filters import (
    _jinja_error_info,
    load_jinja2_filters,
    load_jinja2_filters_from_file,
)
from kapitan.utils.filesystem import file_mode


@lru_cache(maxsize=256)
def render_jinja2_template(content, context):
    """Render jinja2 content with context."""
    return jinja2.Template(content, undefined=jinja2.StrictUndefined).render(context)


def render_jinja2_file(
    name,
    context,
    jinja2_filters=defaults.DEFAULT_JINJA2_FILTERS_PATH,
    search_paths=None,
):
    """Render jinja2 file name with context."""
    path, filename = os.path.split(name)
    search_paths = [path or "./"] + (search_paths or [])
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(search_paths),
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=["jinja2.ext.do"],
    )
    load_jinja2_filters(env)
    load_jinja2_filters_from_file(env, jinja2_filters)
    try:
        return env.get_template(filename).render(context)
    except jinja2.TemplateError as exc:
        err_info = _jinja_error_info(traceback.extract_tb(sys.exc_info()[2]))
        raise CompileError(
            f"Jinja2 TemplateError: {exc}, at {err_info[0]}:{err_info[1]}"
        )


def render_jinja2(
    path,
    context,
    jinja2_filters=defaults.DEFAULT_JINJA2_FILTERS_PATH,
    search_paths=None,
):
    """
    Render files in path with context.
    Returns a dict keyed by the filename (with subpath) with content and mode.
    Ignores hidden files.
    """
    rendered = {}
    if os.path.isfile(path):
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        walk_root_files = [(dirname, None, [basename])]
    else:
        walk_root_files = os.walk(path)

    for root, _, files in walk_root_files:
        for name in files:
            if name.startswith("."):
                continue
            render_path = os.path.join(root, name)
            subpath = render_path[len(os.path.commonprefix([root, path])) :].strip("/")
            try:
                rendered[subpath] = {
                    "content": render_jinja2_file(
                        render_path,
                        context,
                        jinja2_filters=jinja2_filters,
                        search_paths=search_paths,
                    ),
                    "mode": file_mode(render_path),
                }
            except Exception as exc:
                raise CompileError(
                    f"Jinja2 error: failed to render {render_path}: {exc}"
                )

    return rendered
