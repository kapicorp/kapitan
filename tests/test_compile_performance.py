#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Performance benchmarks for Kapitan compilation.

These tests use pytest-benchmark to measure compile throughput.
Run locally with: uv run pytest tests/test_compile_performance.py -v --no-cov -p no:xdist
"""

import os

import pytest

from kapitan import cached
from kapitan.cli import build_parser
from kapitan.inventory import InventoryBackends
from kapitan.resources import inventory as get_inventory
from tests.test_helpers import CompileTestHelper


PROFILE_DIR = os.environ.get("KAPITAN_BENCHMARK_PROFILE_DIR", "kapitan-profiles")
PROFILE_ARGS = [
    "--profile",
    "--profile-serial",
    "--profile-format",
    "json",
    "--memory-profile",
    "--profile-output-dir",
    PROFILE_DIR,
]


def _render_inventory(backend: InventoryBackends = None):
    """Render inventory with optional backend override."""
    cached.reset_cache()
    args = ["compile"]
    if backend is not None:
        args.extend(["--inventory-backend", str(backend)])
    cached.args = build_parser().parse_args(args)
    get_inventory(inventory_path=".")


@pytest.mark.slow
@pytest.mark.integration
def test_compile_performance_with_profiling(isolated_performance_inventory):
    """Run a single compile with profiling enabled to generate flame graphs.

    Not benchmarked — exists purely to produce --profile and --memory-profile
    artifacts for CI download. Uses --profile-serial so the report captures the
    full call tree (kadet/jinja/jsonnet internals) in one unified flame graph.
    """
    helper = CompileTestHelper(isolated_performance_inventory)
    # Profiling flags are top-level arguments and must come BEFORE the subcommand.
    helper.compile_with_args(
        [*PROFILE_ARGS, "compile", "--inventory-path", ".", "--parallelism", "1"],
    )


@pytest.mark.benchmark(max_time=10.0)
@pytest.mark.slow
@pytest.mark.integration
def test_compile_performance_inventory(benchmark, isolated_performance_inventory):
    """Benchmark full compile of the performance stress inventory."""
    helper = CompileTestHelper(isolated_performance_inventory)
    benchmark(
        helper.compile_targets,
        extra_args=["--inventory-path", ".", "--parallelism", "1"],
    )


@pytest.mark.benchmark(max_time=10.0)
@pytest.mark.slow
@pytest.mark.integration
def test_compile_performance_inventory_reclass_rs(
    benchmark, isolated_performance_inventory
):
    """Benchmark performance inventory with reclass-rs backend."""
    helper = CompileTestHelper(isolated_performance_inventory)
    benchmark(
        helper.compile_targets,
        extra_args=[
            "--inventory-path",
            ".",
            "--inventory-backend",
            str(InventoryBackends.RECLASS_RS),
            "--parallelism",
            "1",
        ],
    )


@pytest.mark.benchmark(max_time=10.0)
@pytest.mark.slow
@pytest.mark.integration
def test_compile_performance_inventory_omegaconf(
    benchmark, isolated_performance_inventory
):
    """Benchmark performance inventory with omegaconf backend."""
    helper = CompileTestHelper(isolated_performance_inventory)
    benchmark(
        helper.compile_targets,
        extra_args=[
            "--inventory-path",
            ".",
            "--inventory-backend",
            str(InventoryBackends.OMEGACONF),
            "--parallelism",
            "1",
        ],
    )


@pytest.mark.benchmark(max_time=1.0)
@pytest.mark.slow
@pytest.mark.integration
def test_inventory_render_performance(benchmark, isolated_performance_inventory):
    """Benchmark inventory rendering only (no compilation)."""
    benchmark(_render_inventory)


@pytest.mark.benchmark(max_time=1.0)
@pytest.mark.slow
@pytest.mark.integration
def test_inventory_render_performance_reclass_rs(
    benchmark, isolated_performance_inventory
):
    """Benchmark inventory rendering with reclass-rs backend."""
    benchmark(_render_inventory, InventoryBackends.RECLASS_RS)


@pytest.mark.benchmark(max_time=1.0)
@pytest.mark.slow
@pytest.mark.integration
def test_inventory_render_performance_omegaconf(
    benchmark, isolated_performance_inventory
):
    """Benchmark inventory rendering with omegaconf backend."""
    benchmark(_render_inventory, InventoryBackends.OMEGACONF)


@pytest.mark.benchmark(max_time=2.0)
@pytest.mark.slow
@pytest.mark.integration
def test_inventory_render_performance_synthetic(benchmark, synthetic_large_inventory):
    """Benchmark rendering of the generated shared-class-stack inventory."""
    benchmark(_render_inventory)


@pytest.mark.benchmark(max_time=2.0)
@pytest.mark.slow
@pytest.mark.integration
def test_inventory_render_performance_synthetic_reclass_rs(
    benchmark, synthetic_large_inventory
):
    """Benchmark the synthetic shared-class-stack with reclass-rs backend."""
    benchmark(_render_inventory, InventoryBackends.RECLASS_RS)


@pytest.mark.benchmark(max_time=2.0)
@pytest.mark.slow
@pytest.mark.integration
def test_inventory_render_performance_synthetic_omegaconf(
    benchmark, synthetic_large_inventory
):
    """Benchmark the synthetic shared-class-stack with omegaconf backend."""
    benchmark(_render_inventory, InventoryBackends.OMEGACONF)
