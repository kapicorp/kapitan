#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Regenerate the golden compiled snapshots for inventory backend examples.

Usage:
    make refresh-inventory-backend-goldens
    # or directly:
    uv run python scripts/refresh_inventory_backend_goldens.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _import_inventory_backend_examples():
    """Import tests.inventory_backend_examples after adjusting sys.path."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    from tests.inventory_backend_examples import INVENTORY_BACKEND_EXAMPLES

    return INVENTORY_BACKEND_EXAMPLES


def refresh_one(scenario) -> None:
    print(f"[refresh-goldens] {scenario.name}: copying example tree", flush=True)
    with tempfile.TemporaryDirectory(prefix=f"kapitan_golden_{scenario.name}_") as tmp:
        work = os.path.join(tmp, scenario.name)
        shutil.copytree(scenario.source_dir, work)

        compiled = os.path.join(work, "compiled")
        if os.path.exists(compiled):
            shutil.rmtree(compiled)

        argv_str = " ".join(scenario.compile_args)
        print(
            f"[refresh-goldens] {scenario.name}: running kapitan {argv_str}",
            flush=True,
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        subprocess.run(
            [sys.executable, "-m", "kapitan", *scenario.compile_args],
            cwd=work,
            check=True,
            env=env,
        )

        if not os.path.isdir(compiled):
            raise SystemExit(
                f"[refresh-goldens] {scenario.name}: compile produced no `compiled/` directory"
            )

        print(
            f"[refresh-goldens] {scenario.name}: replacing {scenario.golden_dir}",
            flush=True,
        )
        if os.path.exists(scenario.golden_dir):
            shutil.rmtree(scenario.golden_dir)
        shutil.copytree(compiled, scenario.golden_dir)


def main() -> int:
    INVENTORY_BACKEND_EXAMPLES = _import_inventory_backend_examples()
    for scenario in INVENTORY_BACKEND_EXAMPLES:
        refresh_one(scenario)
    print(
        "[refresh-goldens] Done. Review `git status` / `git diff` and commit the "
        "snapshot changes alongside the source change that produced them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
