# ruff: noqa: INP001 (docs/ is not an importable package; loaded by mkdocs as a hook)
"""MkDocs build hook that injects auto-generated CLI flag tables.

Pages drop a marker comment and this hook replaces it, at build time, with a
Markdown table generated from Kapitan's argument parser (see `gen_flags.py`):

    <!-- kapitan-flags:global -->            -> table of global flags
    <!-- kapitan-flags:dotfile -->           -> per-section `.kapitan` tables
    <!-- kapitan-flags:command:compile -->   -> flag table for one subcommand

The generated Markdown is returned as page source, so it flows through the
normal MkDocs pipeline exactly once. (An earlier `markdown-exec` version was
dropped: re-rendering the output a second time made `pymdownx.inlinehilite`
backtrack catastrophically on the many inline-code cells and hang the build.)
"""

import os
import re
import sys


sys.path.insert(0, os.path.dirname(__file__))

from gen_flags import command_reference, dotfile_reference, global_reference


_MARKER = re.compile(r"<!--\s*kapitan-flags:(global|dotfile|command:[a-z]+)\s*-->")


def _replace(match):
    token = match.group(1)
    if token == "global":
        return global_reference()
    if token == "dotfile":
        return dotfile_reference()
    return command_reference(token.split(":", 1)[1])


def on_page_markdown(markdown, **kwargs):
    return _MARKER.sub(_replace, markdown)
