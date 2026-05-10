#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for scripts/check_coverage.py (FR-014)."""

import importlib.util
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Load the script as a module without adding scripts/ to sys.path permanently.
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "check_coverage.py"


def _load_check_coverage():
    spec = importlib.util.spec_from_file_location("check_coverage", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check_coverage = _load_check_coverage()


# ---------------------------------------------------------------------------
# Tests for check_module_thresholds
# ---------------------------------------------------------------------------


def _make_coverage(overrides: dict[str, float] | None = None) -> dict[str, float]:
    """Return a synthetic coverage dict where every module in MODULE_THRESHOLDS
    is 5 pp above its configured threshold (i.e. passing), then apply any
    *overrides* on top."""
    result = {
        module: threshold + 5.0
        for module, threshold in check_coverage.MODULE_THRESHOLDS.items()
    }
    if overrides:
        result.update(overrides)
    return result


def test_all_modules_above_threshold_produces_no_failures():
    coverage = _make_coverage()
    failures = check_coverage.check_module_thresholds(coverage)
    assert failures == []


def test_single_module_below_threshold_is_reported():
    target = "kapitan/cli.py"
    threshold = check_coverage.MODULE_THRESHOLDS[target]
    coverage = _make_coverage({target: threshold - 1.0})

    failures = check_coverage.check_module_thresholds(coverage)

    assert len(failures) == 1
    module, actual, reported_threshold = failures[0]
    assert module == target
    assert actual == pytest.approx(threshold - 1.0)
    assert reported_threshold == threshold


def test_multiple_modules_below_threshold_all_reported():
    targets = [
        "kapitan/targets.py",
        "kapitan/refs/base.py",
        "kapitan/refs/secrets/gpg.py",
    ]
    overrides = {m: check_coverage.MODULE_THRESHOLDS[m] - 2.0 for m in targets}
    coverage = _make_coverage(overrides)

    failures = check_coverage.check_module_thresholds(coverage)
    failed_modules = {f[0] for f in failures}

    assert failed_modules == set(targets)


def test_module_at_exact_threshold_passes():
    target = "kapitan/dependency_manager/base.py"
    threshold = check_coverage.MODULE_THRESHOLDS[target]
    coverage = _make_coverage({target: float(threshold)})

    failures = check_coverage.check_module_thresholds(coverage)
    assert all(f[0] != target for f in failures)


def test_unknown_module_in_coverage_data_is_ignored():
    coverage = _make_coverage({"kapitan/some_new_module.py": 0.0})
    failures = check_coverage.check_module_thresholds(coverage)
    assert all(f[0] != "kapitan/some_new_module.py" for f in failures)


def test_module_missing_from_coverage_data_counts_as_zero():
    target = "kapitan/refs/vault_resources.py"
    threshold = check_coverage.MODULE_THRESHOLDS[target]
    # Build coverage dict that omits the target entirely.
    coverage = {m: v for m, v in _make_coverage().items() if m != target}

    failures = check_coverage.check_module_thresholds(coverage)
    failed_modules = [f[0] for f in failures]

    assert target in failed_modules
    actual = next(f[1] for f in failures if f[0] == target)
    assert actual == 0.0


def test_custom_thresholds_override_defaults():
    custom = {"kapitan/cli.py": 99}
    coverage = {"kapitan/cli.py": 50.0}

    failures = check_coverage.check_module_thresholds(coverage, thresholds=custom)

    assert len(failures) == 1
    assert failures[0][0] == "kapitan/cli.py"
    assert failures[0][2] == 99


# ---------------------------------------------------------------------------
# Integration: main() exits non-zero when .coverage file is missing
# ---------------------------------------------------------------------------


def test_main_returns_2_when_data_file_missing(tmp_path):
    rc = check_coverage.main(["--data-file", str(tmp_path / "nonexistent.coverage")])
    assert rc == 2
