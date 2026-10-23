#!/usr/bin/env python3
"""Generate a markdown profiling summary from pyinstrument + tracemalloc output.

Reads the most recent JSON CPU profile and memory text report from the given
profile directory and writes a formatted markdown summary to GITHUB_STEP_SUMMARY.
"""

import json
import os
import sys
from pathlib import Path


def _collect_frames(node, rows=None):
    if rows is None:
        rows = []
    children = node.get("children", [])
    children_time = sum(c["time"] for c in children)
    rows.append(
        {
            "function": node["function"],
            "file": node.get("file_path_short", node.get("file_path", "")),
            "line": node.get("line_no", 0),
            "self": node["time"] - children_time,
            "inclusive": node["time"],
        }
    )
    for child in children:
        _collect_frames(child, rows)
    return rows


def _cpu_table(profile_dir: Path) -> list[str]:
    cpu_json = sorted(profile_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not cpu_json:
        return []

    with open(cpu_json[-1]) as f:
        data = json.load(f)

    rows = _collect_frames(data["root_frame"])
    rows.sort(key=lambda r: r["self"], reverse=True)

    lines = [
        "### CPU Profile (pyinstrument)",
        "",
        "| Function | Self | Inclusive | Location |",
        "|----------|------|-----------|----------|",
    ]

    shown = 0
    for r in rows:
        if r["self"] <= 0.001:
            continue
        if shown >= 12:
            break
        func = r["function"][:28]
        loc = f"{r['file']}:{r['line']}"[:45]
        lines.append(f"| {func} | {r['self']:.3f}s | {r['inclusive']:.3f}s | {loc} |")
        shown += 1
    return lines


def _memory_block(profile_dir: Path) -> list[str]:
    mem_txt = sorted(profile_dir.glob("*.memory.txt"), key=lambda p: p.stat().st_mtime)
    if not mem_txt:
        return []

    lines = ["### Memory Profile (tracemalloc)", "```"]
    header_done = False
    with open(mem_txt[-1]) as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped:
                continue
            if "allocations" in stripped or "peak" in stripped:
                lines.append(stripped)
                header_done = True
            elif header_done and stripped.startswith("#"):
                lines.append(stripped)
                break
        for line in f:
            stripped = line.rstrip()
            if not stripped:
                continue
            if stripped.startswith("Kapitan memory profile"):
                break
            lines.append(stripped)
            if len(lines) > 50:
                break
    lines.append("```")
    return lines


def main():
    profile_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("kapitan-profiles")

    mem_lines = _memory_block(profile_dir)
    if not mem_lines:
        print(
            "Warning: no memory profile files found in "
            f"'{profile_dir}'; skipping memory summary section.",
            file=sys.stderr,
        )

    summary = ["## Profiling Summary", ""]
    summary.extend(_cpu_table(profile_dir))
    if summary[-1] != "":
        summary.append("")
    summary.extend(mem_lines)

    output_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if output_path:
        # Guard against duplicate append if this script is invoked multiple
        # times in the same job.
        if os.path.exists(output_path):
            with open(output_path) as f:
                if "## Profiling Summary" in f.read():
                    return
        with open(output_path, "a") as f:
            f.write("\n".join(summary) + "\n")
    else:
        print("\n".join(summary))


if __name__ == "__main__":
    main()
