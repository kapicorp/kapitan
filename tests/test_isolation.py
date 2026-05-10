#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Meta-test: assert that forbidden isolation anti-patterns are absent from tests/.

Forbidden patterns (per TESTING_BEST_PRACTICES.md and FR-008):
- tempfile.mkdtemp()    — leaks temp directories; use TemporaryDirectory() instead
- sys.path.insert()     — mutates global state; use importlib.util instead
- bare os.chdir()       — only allowed inside the canonical pushd() utility and the
                          reset_environment autouse fixture in conftest.py
"""

import re
from pathlib import Path

import pytest


_TESTS_DIR = Path(__file__).parent

# Allowlist: files/functions where os.chdir is legitimate infrastructure.
# Each entry is a (file_stem, containing_text) pair.  A match means the
# occurrence is accepted.
_CHDIR_ALLOWLIST = [
    # pushd() implementation in conftest.py
    ("conftest", "def pushd"),
    # reset_environment autouse fixture in conftest.py
    ("conftest", "def reset_environment"),
]

# Patterns whose presence in .py test files is forbidden
_FORBIDDEN = {
    "tempfile.mkdtemp": re.compile(r"tempfile\.mkdtemp\s*\("),
    "sys.path.insert": re.compile(r"sys\.path\.insert\s*\("),
}

_CHDIR_PATTERN = re.compile(r"\bos\.chdir\s*\(")


def _load_test_py_files():
    """Yield (path, source) for every .py file in tests/ (excluding this file)."""
    for path in _TESTS_DIR.rglob("*.py"):
        if path == Path(__file__):
            continue
        yield path, path.read_text(encoding="utf-8")


def _is_allowlisted_chdir(file_stem: str, source: str, match_start: int) -> bool:
    """Return True if the os.chdir occurrence is in an allowlisted function."""
    # Find the enclosing function by scanning backwards for the nearest def
    preceding = source[:match_start]
    for stem, func_marker in _CHDIR_ALLOWLIST:
        if file_stem == stem and func_marker in preceding:
            # Verify the def is the most recent one before the match
            last_def_pos = preceding.rfind("def ")
            marker_pos = preceding.rfind(func_marker)
            if marker_pos != -1 and marker_pos >= last_def_pos - len(func_marker) - 10:
                return True
    return False


@pytest.mark.parametrize(("pattern_name", "pattern"), list(_FORBIDDEN.items()))
def test_forbidden_pattern_absent(pattern_name, pattern):
    """Verify that forbidden anti-patterns do not appear in any test file."""
    violations = []
    for path, source in _load_test_py_files():
        for match in pattern.finditer(source):
            line_no = source[: match.start()].count("\n") + 1
            violations.append(f"{path.relative_to(_TESTS_DIR)}:{line_no}")

    assert not violations, (
        f"Forbidden pattern '{pattern_name}' found in tests/:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_os_chdir_only_in_infrastructure():
    """Verify os.chdir() only appears in the canonical pushd() and reset_environment()."""
    violations = []
    for path, source in _load_test_py_files():
        for match in _CHDIR_PATTERN.finditer(source):
            if not _is_allowlisted_chdir(path.stem, source, match.start()):
                line_no = source[: match.start()].count("\n") + 1
                violations.append(f"{path.relative_to(_TESTS_DIR)}:{line_no}")

    assert not violations, (
        "os.chdir() found outside allowed infrastructure in tests/:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\nUse the pushd() context manager from conftest.py or an isolated fixture instead."
    )
