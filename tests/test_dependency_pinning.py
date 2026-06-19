# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Supply-chain guard: every dependency in uv.lock must be hash-pinned.

A hash-pinned lockfile is what stops a tampered or substituted package from
being installed in place of the one we resolved. These tests fail loudly if a
PyPI distribution ever lands in ``uv.lock`` without a ``sha256`` hash, so the
guarantee can't silently regress.

The checks read ``uv.lock`` as text on purpose: ``tomllib`` only ships with
Python 3.11+, and we support 3.10, so a line scan keeps the test working on
every supported interpreter without an extra dependency.
"""

import re
from pathlib import Path

import pytest


LOCKFILE = Path(__file__).resolve().parent.parent / "uv.lock"

# A packaged distribution entry: a wheel or sdist served over http(s).
_DIST_URL = re.compile(r'url = "https?://[^"]+\.(?:whl|tar\.gz|zip)"')
# uv records a sha256 digest inline on the same line as the distribution url.
_SHA256 = re.compile(r'hash = "sha256:[0-9a-f]{64}"')

pytestmark = pytest.mark.unit


def test_lockfile_exists():
    assert LOCKFILE.is_file(), f"expected lockfile at {LOCKFILE}"


def test_every_distribution_is_hash_pinned():
    unpinned = [
        (lineno, line.strip())
        for lineno, line in enumerate(LOCKFILE.read_text().splitlines(), start=1)
        if _DIST_URL.search(line) and not _SHA256.search(line)
    ]
    assert not unpinned, (
        "uv.lock has distributions without a sha256 hash:\n"
        + "\n".join(f"  uv.lock:{lineno}: {line}" for lineno, line in unpinned)
    )


def test_lockfile_actually_contains_hashes():
    # Guards against the scan silently passing on an empty or malformed lock.
    assert _SHA256.search(LOCKFILE.read_text()), "no sha256 hashes found in uv.lock"
