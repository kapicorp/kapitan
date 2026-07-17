# ruff: noqa: INP001 (docs/ is not an importable package; loaded via sys.path)
"""Introspect Kapitan's argparse parser to generate flag-reference tables.

Used at docs-build time by `markdown-exec` blocks so each command page and the
`.kapitan` dotfile reference stay in sync with `kapitan/cli.py` automatically.
There is no generated artifact to commit: the tables are rendered on every
`mkdocs build` from the installed Kapitan, so they can never drift.

Each public function *returns* a Markdown string (rather than printing it) so the
calling exec block can `print()` it — markdown-exec only captures `print` calls
made in the block's own namespace, not in imported helpers.
"""

import argparse

from kapitan.cli import build_parser


def _esc(value):
    """Render a value as a single, table-safe Markdown cell."""
    if value is None or value in ("", []):
        return ""
    if isinstance(value, (list | tuple)):
        text = ", ".join(str(v) for v in value)
    else:
        text = str(value)
    return " ".join(text.replace("|", "\\|").split())


def _default_cell(value):
    """Render a flag default as a code span. Lists become `["a", "b"]` rather
    than a bare `a, b`, which reads ambiguously in a table cell."""
    if value is None or value in ("", []):
        return ""
    if isinstance(value, (list | tuple)):
        items = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in value)
        text = f"[{items}]"
    else:
        text = str(value)
    safe = " ".join(text.replace("|", "\\|").split())
    return f"`{safe}`"


def _subcommands(parser):
    """Yield (name, subparser) for each subcommand, skipping alias duplicates."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            seen = set()
            for name, subparser in action.choices.items():
                if id(subparser) in seen:
                    continue  # alias of an already-emitted parser (e.g. `c` -> compile)
                seen.add(id(subparser))
                yield name, subparser


def _flag_rows(parser):
    """Yield dicts describing each user-facing argument of a parser."""
    for action in parser._actions:
        if isinstance(action, (argparse._HelpAction | argparse._SubParsersAction)):
            continue
        if action.option_strings == ["--version"] or isinstance(
            action, argparse._VersionAction
        ):
            continue
        opts = list(dict.fromkeys(action.option_strings))  # dedup, keep order
        yield {
            "options": ", ".join(f"`{o}`" for o in opts) or f"`{action.dest}`",
            # dotfile key: long flag, dashes kept, leading -- stripped
            "key": next(
                (o.lstrip("-") for o in action.option_strings if o.startswith("--")),
                action.dest,
            ),
            "positional": not action.option_strings,
            "default": action.default,
            "choices": list(action.choices) if action.choices else None,
            "help": action.help,
        }


def _flag_table(rows):
    """Return a Markdown flag table (or a placeholder when there are no flags)."""
    flags = [r for r in rows if not r["positional"]]
    if not flags:
        return "_This command takes no optional flags._"
    lines = ["| Flag | Default | Choices | Description |", "| --- | --- | --- | --- |"]
    for r in flags:
        lines.append(
            f"| {r['options']} | {_default_cell(r['default'])} "
            f"| {_esc(r['choices'])} | {_esc(r['help'])} |"
        )
    return "\n".join(lines)


def _find_subparser(command):
    for name, subparser in _subcommands(build_parser()):
        if name == command:
            return subparser
    raise KeyError(f"unknown kapitan subcommand: {command!r}")


def global_reference():
    """Return the table of global flags accepted by every `kapitan` invocation."""
    return _flag_table(list(_flag_rows(build_parser())))


def command_reference(command):
    """Return the flag table (and positional args) for a single subcommand."""
    rows = list(_flag_rows(_find_subparser(command)))
    positionals = [r for r in rows if r["positional"]]
    parts = []
    if positionals:
        parts.append("**Arguments:** " + ", ".join(r["options"] for r in positionals))
    parts.append(_flag_table(rows))
    return "\n\n".join(parts)


def _dotfile_table(rows):
    """Return a `.kapitan` table (Key/Default/Description), or None if no flags."""
    flags = [r for r in rows if not r["positional"]]
    if not flags:
        return None
    lines = ["| Key | Default | Description |", "| --- | --- | --- |"]
    for r in flags:
        lines.append(
            f"| `{r['key']}` | {_default_cell(r['default'])} | {_esc(r['help'])} |"
        )
    return "\n".join(lines)


def dotfile_reference():
    """Return Markdown `.kapitan` flag tables, one `###` section per command."""
    parser = build_parser()
    sections = [("global", list(_flag_rows(parser)))]
    sections += [(name, list(_flag_rows(sub))) for name, sub in _subcommands(parser)]

    out = []
    for name, rows in sections:
        table = _dotfile_table(rows)
        if table is None:
            continue  # e.g. deprecated `secrets` has no settable flags
        out.append(f"### `{name}`\n\n{table}")
    return "\n\n".join(out)


if __name__ == "__main__":
    # Invoked as a subprocess by the docs exec blocks so Kapitan's heavy imports
    # (cloud SDKs, etc.) load in a short-lived process and never weigh down the
    # mkdocs build process. Usage: gen_flags.py {global|dotfile|command <name>}
    import sys

    mode = sys.argv[1]
    if mode == "global":
        print(global_reference())
    elif mode == "dotfile":
        print(dotfile_reference())
    elif mode == "command":
        print(command_reference(sys.argv[2]))
    else:
        raise SystemExit(f"unknown mode: {mode!r}")
