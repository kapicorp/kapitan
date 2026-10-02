"""Tests for the docs flag-reference generator (`docs/gen_flags.py`).

`mkdocs build` does NOT fail when a generated table yields empty output, so a
regression in the generator (or a new CLI subcommand added without a docs page)
would ship silent empty tables. Most tests here exercise the generator directly,
without building the docs site.

`test_mkdocs_build_completes` is the exception: it runs a real, timeout-guarded
build. This guards the class of bug that once hung the docs build — a second
Markdown render pass (markdown-exec) over the generated inline-code tables made
`pymdownx.inlinehilite` backtrack catastrophically and spin forever. A hang is
invisible to a plain `mkdocs build` (it just never returns), so the timeout
converts "hangs in CI until the job dies" into "fails locally in minutes".
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
COMMANDS_DIR = DOCS_DIR / "pages" / "commands"

# Subcommands intentionally not given a flag table (e.g. deprecated, no flags).
EXCLUDED_SUBCOMMANDS = {"secrets"}

sys.path.insert(0, str(DOCS_DIR))
import gen_flags  # noqa: E402

from kapitan.cli import build_parser  # noqa: E402


def _real_subcommands():
    return [name for name, _ in gen_flags._subcommands(build_parser())]


def _documented_subcommands():
    """Subcommands embedded via a `<!-- kapitan-flags:command:x -->` marker."""
    documented = set()
    for page in COMMANDS_DIR.glob("kapitan_*.md"):
        documented.update(
            re.findall(r"<!--\s*kapitan-flags:command:(\w+)\s*-->", page.read_text())
        )
    return documented


@pytest.mark.unit
def test_every_subcommand_is_documented_or_excluded():
    """A new CLI subcommand must get a docs page (or be explicitly excluded)."""
    missing = (
        set(_real_subcommands()) - _documented_subcommands() - EXCLUDED_SUBCOMMANDS
    )
    assert not missing, (
        f"subcommands with no docs flag table: {sorted(missing)}. "
        f"Add a page embedding command_reference(), or add to EXCLUDED_SUBCOMMANDS."
    )


@pytest.mark.unit
def test_documented_subcommands_are_real():
    """Guard against typos / removed commands in the docs exec blocks."""
    bogus = _documented_subcommands() - set(_real_subcommands())
    assert not bogus, f"docs reference non-existent subcommands: {sorted(bogus)}"


@pytest.mark.unit
@pytest.mark.parametrize("command", _real_subcommands())
def test_command_reference_renders(command):
    out = gen_flags.command_reference(command)
    assert out.strip(), f"empty output for {command!r}"
    # Either a real flag table or the explicit no-flags placeholder.
    assert "| Flag | Default | Choices | Description |" in out or "no optional" in out


@pytest.mark.unit
def test_global_reference_has_known_flag():
    out = gen_flags.global_reference()
    assert "| Flag |" in out
    assert "mp-method" in out  # a stable global flag


@pytest.mark.unit
def test_dotfile_reference_has_section_per_command_with_flags():
    out = gen_flags.dotfile_reference()
    assert "### `global`" in out
    for command in _real_subcommands():
        has_flags = any(
            not r["positional"]
            for r in gen_flags._flag_rows(gen_flags._find_subparser(command))
        )
        if has_flags:
            assert f"### `{command}`" in out, f"missing dotfile section for {command}"


@pytest.mark.unit
def test_table_rows_keep_four_columns():
    """A raw `|` in help/defaults would split a cell and break the 4-col layout."""
    for command in _real_subcommands():
        for line in gen_flags.command_reference(command).splitlines():
            if line.startswith("|"):
                unescaped = len(re.findall(r"(?<!\\)\|", line))
                assert unescaped == 5, f"{command}: malformed table row: {line!r}"


@pytest.mark.slow
@pytest.mark.integration
def test_mkdocs_build_completes():
    """Full docs build must finish (and inject tables) — catches build hangs.

    The timeout is the point: a render regression spins forever rather than
    erroring, so without it CI would hang instead of fail.
    """
    with tempfile.TemporaryDirectory() as site_dir:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "mkdocs", "build", "--strict", "-d", site_dir],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(
                "mkdocs build did not finish within 300s (likely a render hang)"
            )
        assert result.returncode == 0, f"mkdocs build failed:\n{result.stderr[-2000:]}"
        # The hook must have injected a real table, not left the marker behind.
        compiled = (
            Path(site_dir) / "pages" / "commands" / "kapitan_compile" / "index.html"
        )
        html = compiled.read_text()
        assert "kapitan-flags:" not in html, "marker comment was not replaced"
        assert "<td>" in html, "no table rendered on the compile page"
