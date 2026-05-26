# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""
CPU and memory profiling helpers for Kapitan.

CPU profiling is provided by `pyinstrument` (optional dependency: install with
`pip install kapitan[profile]`). Memory profiling uses the `tracemalloc`
module from the Python standard library, so it has no extra dependencies.

This module is import-safe even when `pyinstrument` is not installed: the
import is deferred until profiling is actually requested.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


logger = logging.getLogger(__name__)

# Env vars used to propagate profiling settings to multiprocessing workers.
# Pool workers (spawn/fork/forkserver) inherit the parent's environment, so
# this is the simplest reliable channel.
ENV_WORKER_DIR = "KAPITAN_PROFILE_WORKERS_DIR"
ENV_WORKER_FORMAT = "KAPITAN_PROFILE_WORKERS_FORMAT"
ENV_WORKER_INTERVAL = "KAPITAN_PROFILE_WORKERS_INTERVAL"

_VALID_FORMATS = ("html", "text", "json", "speedscope")


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")


def _ensure_dir(path: str | os.PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _import_pyinstrument():
    """Import pyinstrument lazily and emit a helpful error if missing."""
    try:
        import pyinstrument
    except ImportError as e:  # pragma: no cover - depends on optional install
        raise SystemExit(
            "Profiling requested but `pyinstrument` is not installed.\n"
            "Install the optional dependency with:\n"
            "    pip install 'kapitan[profile]'\n"
            f"(original error: {e})"
        ) from e
    else:
        return pyinstrument


def _render_pyinstrument(profiler, fmt: str) -> tuple[str, str]:
    """Return (rendered_output, file_extension) for a finished Profiler."""
    fmt = fmt.lower()
    if fmt not in _VALID_FORMATS:
        raise ValueError(
            f"Invalid profile format {fmt!r}; choose one of {_VALID_FORMATS}"
        )
    if fmt == "html":
        return profiler.output_html(), "html"
    if fmt == "json":
        return profiler.output(
            renderer=__import__(
                "pyinstrument.renderers", fromlist=["JSONRenderer"]
            ).JSONRenderer()
        ), "json"
    if fmt == "speedscope":
        return profiler.output(
            renderer=__import__(
                "pyinstrument.renderers", fromlist=["SpeedscopeRenderer"]
            ).SpeedscopeRenderer()
        ), "speedscope.json"
    # text
    return profiler.output_text(unicode=True, color=False), "txt"


@contextlib.contextmanager
def cpu_profile(args) -> Iterator[None]:
    """
    Context manager that runs `pyinstrument` around the wrapped block when
    `args.profile` is truthy. Writes a report to
    `<profile_output_dir>/kapitan-<subcmd>-<ts>-pid<pid>.<ext>`.

    Also sets env vars so that multiprocessing workers self-profile when
    `args.profile_workers` is set.
    """
    if not getattr(args, "profile", False):
        yield
        return

    pyinstrument = _import_pyinstrument()

    interval = float(getattr(args, "profile_interval", 0.001) or 0.001)
    fmt = getattr(args, "profile_format", "html") or "html"
    out_dir = _ensure_dir(getattr(args, "profile_output_dir", "kapitan-profiles"))

    if getattr(args, "profile_workers", False):
        os.environ[ENV_WORKER_DIR] = str(out_dir)
        os.environ[ENV_WORKER_FORMAT] = fmt
        os.environ[ENV_WORKER_INTERVAL] = str(interval)
        logger.info("Worker CPU profiling enabled; per-PID reports → %s", out_dir)

    profiler = pyinstrument.Profiler(interval=interval, async_mode="enabled")
    profiler.start()
    logger.info(
        "CPU profiling enabled (pyinstrument, interval=%.4fs, format=%s)",
        interval,
        fmt,
    )
    try:
        yield
    finally:
        profiler.stop()
        subcmd = getattr(args, "subparser_name", None) or "kapitan"
        try:
            rendered, ext = _render_pyinstrument(profiler, fmt)
        except Exception as e:  # pragma: no cover - defensive
            logger.error("Failed to render profile: %s", e)
            return
        out_path = out_dir / f"kapitan-{subcmd}-{_timestamp()}-pid{os.getpid()}.{ext}"
        out_path.write_text(rendered)
        logger.info("CPU profile written: %s", out_path)
        # When in text mode, also echo a short summary to stderr so users see it.
        if fmt == "text":
            print("\n=== Kapitan CPU profile (pyinstrument) ===", file=sys.stderr)
            print(rendered, file=sys.stderr)


@contextlib.contextmanager
def memory_profile(args) -> Iterator[None]:
    """
    Context manager that uses `tracemalloc` to take before/after snapshots
    around the wrapped block when `args.memory_profile` is truthy, and
    writes the top-N allocation diff to a text report.
    """
    if not getattr(args, "memory_profile", False):
        yield
        return

    top_n = int(getattr(args, "memory_profile_top", 30) or 30)
    out_dir = _ensure_dir(getattr(args, "profile_output_dir", "kapitan-profiles"))

    # Start tracking. nframes=10 keeps stack depth informative without
    # blowing up overhead too much.
    tracemalloc.start(10)
    logger.info("Memory profiling enabled (tracemalloc, top=%d)", top_n)
    snapshot_before = tracemalloc.take_snapshot()
    try:
        yield
    finally:
        snapshot_after = tracemalloc.take_snapshot()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        stats = snapshot_after.compare_to(snapshot_before, "lineno")[:top_n]
        subcmd = getattr(args, "subparser_name", None) or "kapitan"
        out_path = (
            out_dir / f"kapitan-{subcmd}-{_timestamp()}-pid{os.getpid()}.memory.txt"
        )

        lines = [
            "Kapitan memory profile (tracemalloc)",
            f"  current allocations at end of run: {current / (1024 * 1024):.2f} MiB",
            f"  peak allocations during run:       {peak / (1024 * 1024):.2f} MiB",
            f"  top {top_n} allocation deltas:",
            "",
        ]
        for i, stat in enumerate(stats, 1):
            lines.append(f"#{i}: {stat}")
            for tb_line in stat.traceback.format():
                lines.append(f"    {tb_line}")
            lines.append("")

        report = "\n".join(lines)
        out_path.write_text(report)
        logger.info("Memory profile written: %s", out_path)


@contextlib.contextmanager
def worker_profile() -> Iterator[None]:
    """
    Context manager used inside multiprocessing workers. Activates only when
    the parent has set `KAPITAN_PROFILE_WORKERS_DIR` (i.e. user passed
    `--profile-workers`). Each worker dumps its own per-PID report.
    """
    out_dir = os.environ.get(ENV_WORKER_DIR)
    if not out_dir:
        yield
        return

    try:
        pyinstrument = _import_pyinstrument()
    except SystemExit:
        # In a worker, never abort the run because of profiling setup failures.
        logger.warning("Worker profiling requested but pyinstrument not available")
        yield
        return

    fmt = os.environ.get(ENV_WORKER_FORMAT, "html")
    try:
        interval = float(os.environ.get(ENV_WORKER_INTERVAL, "0.001"))
    except ValueError:
        interval = 0.001

    profiler = pyinstrument.Profiler(interval=interval, async_mode="enabled")
    profiler.start()
    try:
        yield
    finally:
        profiler.stop()
        try:
            rendered, ext = _render_pyinstrument(profiler, fmt)
        except Exception as e:  # pragma: no cover - defensive
            logger.error("Worker %d failed to render profile: %s", os.getpid(), e)
            return
        out_path = Path(out_dir) / (
            f"kapitan-worker-{_timestamp()}-pid{os.getpid()}.{ext}"
        )
        try:
            out_path.write_text(rendered)
            logger.debug("Worker CPU profile written: %s", out_path)
        except OSError as e:  # pragma: no cover - defensive
            logger.error("Failed to write worker profile %s: %s", out_path, e)


def add_profiling_arguments(parser) -> None:
    """Register profiling-related CLI flags on the top-level parser."""
    group = parser.add_argument_group(
        "profiling",
        "Optional CPU (pyinstrument) and memory (tracemalloc) profiling. "
        "Install pyinstrument with: pip install 'kapitan[profile]'",
    )
    group.add_argument(
        "--profile",
        action="store_true",
        default=False,
        help="enable CPU profiling via pyinstrument for the parent process",
    )
    group.add_argument(
        "--profile-workers",
        action="store_true",
        default=False,
        help=(
            "also CPU-profile multiprocessing workers; one report per worker PID. Requires --profile."
        ),
    )
    group.add_argument(
        "--profile-serial",
        action="store_true",
        default=False,
        help=(
            "run target compilation serially in the parent process (no "
            "multiprocessing.Pool). Produces a single unified pyinstrument "
            "report with full call-stack depth. Slower wall-clock but the "
            "only way to see *all* stacks (including kadet/jinja/jsonnet "
            "internals) in one flame graph. Implies/pairs well with --profile."
        ),
    )
    group.add_argument(
        "--profile-format",
        choices=list(_VALID_FORMATS),
        default="html",
        help="pyinstrument output format (default: html)",
    )
    group.add_argument(
        "--profile-interval",
        type=float,
        default=0.001,
        help="pyinstrument sampling interval in seconds (default: 0.001)",
    )
    group.add_argument(
        "--profile-output-dir",
        default="kapitan-profiles",
        help="directory for profile reports (default: ./kapitan-profiles)",
    )
    group.add_argument(
        "--memory-profile",
        action="store_true",
        default=False,
        help="enable memory profiling via tracemalloc; writes a top-N text report",
    )
    group.add_argument(
        "--memory-profile-top",
        type=int,
        default=30,
        help="number of top allocators to include in the memory report (default: 30)",
    )
