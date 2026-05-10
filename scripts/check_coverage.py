#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Per-module coverage gate for security-sensitive Kapitan modules.

Usage::

    python scripts/check_coverage.py [--data-file .coverage]

Exits 0 when all configured modules meet their threshold, non-zero otherwise.

Rationale for thresholds
------------------------
These floors were measured on 2026-05-10 and set ~2 pp below the measured value
to act as ratchets.  CI will fail if any module regresses below its floor; the
floor should be bumped upward as new tests are added.

Module                                    Threshold  Rationale
kapitan/cli.py                            12 %       Entry point; hard to unit-test, but shouldn't regress.
kapitan/targets.py                         7 %       Core compile orchestration; high complexity, low baseline.
kapitan/dependency_manager/base.py        15 %       Network IO + retry logic (FR-012); actively being improved.
kapitan/refs/base.py                      12 %       Core ref/secret machinery.
kapitan/refs/cmd_parser.py                 4 %       Complex parser; very low baseline.
kapitan/refs/functions.py                 19 %       Secret backend dispatch.
kapitan/refs/secrets/awskms.py            17 %       AWS KMS backend.
kapitan/refs/secrets/azkms.py            19 %       Azure KMS backend.
kapitan/refs/secrets/gkms.py             19 %       GCP KMS backend.
kapitan/refs/secrets/gpg.py              18 %       GPG backend.
kapitan/refs/secrets/vaultkv.py          10 %       Vault KV backend.
kapitan/refs/secrets/vaulttransit.py     17 %       Vault Transit backend.
kapitan/refs/vault_resources.py          10 %       Vault shared resources.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile


# ---------------------------------------------------------------------------
# Per-module floor thresholds (integer percent)
# ---------------------------------------------------------------------------

MODULE_THRESHOLDS: dict[str, int] = {
    "kapitan/cli.py": 12,
    "kapitan/targets.py": 7,
    "kapitan/dependency_manager/base.py": 15,
    "kapitan/refs/base.py": 12,
    "kapitan/refs/cmd_parser.py": 4,
    "kapitan/refs/functions.py": 19,
    "kapitan/refs/secrets/awskms.py": 17,
    "kapitan/refs/secrets/azkms.py": 19,
    "kapitan/refs/secrets/gkms.py": 19,
    "kapitan/refs/secrets/gpg.py": 18,
    "kapitan/refs/secrets/vaultkv.py": 10,
    "kapitan/refs/secrets/vaulttransit.py": 17,
    "kapitan/refs/vault_resources.py": 10,
}


def load_module_coverage(data_file: str = ".coverage") -> dict[str, float]:
    """Load coverage data and return ``{rel_path: percent_covered}`` for every measured file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "json",
                f"--data-file={data_file}",
                "-o",
                tmp_path,
                "--quiet",
                "--fail-under=0",
            ],
            check=True,
            capture_output=True,
        )
        with open(tmp_path) as f:
            data = json.load(f)
    finally:
        os.unlink(tmp_path)

    project_root = os.getcwd()
    result: dict[str, float] = {}
    for abs_path, info in data.get("files", {}).items():
        rel = os.path.relpath(abs_path, project_root)
        result[rel] = info["summary"]["percent_covered"]
    return result


def check_module_thresholds(
    module_coverage: dict[str, float],
    thresholds: dict[str, int] | None = None,
) -> list[tuple[str, float, int]]:
    """Return a list of ``(module, actual_pct, threshold_pct)`` for every failing module.

    *module_coverage* maps normalised relative paths to their measured coverage
    percentage (float).  Modules present in *thresholds* but absent from
    *module_coverage* are reported as 0 % covered.
    """
    if thresholds is None:
        thresholds = MODULE_THRESHOLDS

    failures: list[tuple[str, float, int]] = []
    for module, threshold in thresholds.items():
        # Normalise separator so the dict works on Windows too.
        norm = module.replace("/", os.sep)
        actual = module_coverage.get(norm, module_coverage.get(module, 0.0))
        if actual < threshold:
            failures.append((module, actual, threshold))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-file",
        default=".coverage",
        metavar="FILE",
        help="path to the .coverage data file (default: .coverage)",
    )
    args = parser.parse_args(argv)

    if not os.path.exists(args.data_file):
        print(
            f"ERROR: coverage data file '{args.data_file}' not found.", file=sys.stderr
        )
        print(
            "Run 'python -m pytest' first to generate coverage data.", file=sys.stderr
        )
        return 2

    module_coverage = load_module_coverage(args.data_file)
    failures = check_module_thresholds(module_coverage)

    col_w = max(len(m) for m in MODULE_THRESHOLDS) + 2
    print(f"\n{'Module':<{col_w}} {'Actual':>8}  {'Threshold':>10}  Status")
    print("-" * (col_w + 32))

    for module, threshold in sorted(MODULE_THRESHOLDS.items()):
        norm = module.replace("/", os.sep)
        actual = module_coverage.get(norm, module_coverage.get(module, 0.0))
        status = "FAIL" if actual < threshold else "ok"
        print(f"{module:<{col_w}} {actual:>7.1f}%  {threshold:>9}%  {status}")

    print()
    if failures:
        print(f"{len(failures)} module(s) below threshold:", file=sys.stderr)
        for module, actual, threshold in failures:
            print(f"  {module}: {actual:.1f}% < {threshold}%", file=sys.stderr)
        return 1

    print("All modules meet their per-module coverage threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
