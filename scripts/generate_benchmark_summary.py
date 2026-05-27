#!/usr/bin/env python3
"""Generate a markdown benchmark summary from pytest-benchmark JSON output.

Reads benchmark-result.json (produced by --benchmark-json) and writes a
formatted markdown table to the file at GITHUB_STEP_SUMMARY.
"""

import json
import os
import sys


def _fmt_time(seconds: float) -> str:
    if seconds >= 1:
        return f"{seconds:.3f} s"
    if seconds >= 0.001:
        return f"{seconds * 1e3:.3f} ms"
    return f"{seconds * 1e6:.3f} µs"


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "benchmark-result.json"
    with open(input_path) as f:
        data = json.load(f)

    machine = data.get("machine_info", {})
    cpu = machine.get("cpu", {})

    summary = []
    summary.append("## Benchmark Summary")
    summary.append("")
    summary.append(
        f"- **Runner:** {machine.get('node', 'unknown')} "
        f"({machine.get('system', 'unknown')} {machine.get('machine', '')})"
    )
    summary.append(f"- **Python:** {machine.get('python_version', 'unknown')}")
    summary.append(f"- **CPU:** {cpu.get('count', '?')} cores")
    summary.append("")
    summary.append("| Benchmark | Mean | Min | Max | Rounds |")
    summary.append("|-----------|------|-----|-----|--------|")

    for bench in data.get("benchmarks", []):
        name = bench["name"]
        stats = bench["stats"]
        summary.append(
            f"| {name} | {_fmt_time(stats['mean'])} | {_fmt_time(stats['min'])} | "
            f"{_fmt_time(stats['max'])} | {stats['rounds']} |"
        )

    output_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if output_path:
        with open(output_path, "a") as f:
            f.write("\n".join(summary) + "\n")
    else:
        print("\n".join(summary))


if __name__ == "__main__":
    main()
