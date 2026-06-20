---
title: "Profiling Kapitan Runs: CPU and Memory Reports"
description: "Learn how to profile Kapitan CPU and memory usage with pyinstrument and tracemalloc reports."
---

# Profiling Kapitan runs

Kapitan ships with optional CPU and memory profiling that you can enable from
any subcommand (`compile`, `inventory`, `eval`, …). Reports are written to a
configurable output directory, one file per run (and per worker PID, if you
opt in).

## Quick start

CPU profiling uses [`pyinstrument`](https://github.com/joerick/pyinstrument)
(optional dependency). Memory profiling uses the standard library
`tracemalloc` module and needs no extra install.

```bash
# install the optional CPU profiler
pip install 'kapitan[profile]'

# CPU profile a compile run, write an interactive HTML report
kapitan --profile compile

# CPU + memory profile, with workers, custom output dir
kapitan --profile --profile-workers --memory-profile \
        --profile-output-dir ./profiles \
        compile

# Text report straight to a file (and stderr summary)
kapitan --profile --profile-format text compile
```

By default reports land in `./kapitan-profiles/`:

```
kapitan-profiles/
├── kapitan-compile-20260508-101502-pid12345.html        # parent CPU
├── kapitan-worker-20260508-101503-pid12346.html         # worker CPU (--profile-workers)
├── kapitan-worker-20260508-101503-pid12347.html
└── kapitan-compile-20260508-101502-pid12345.memory.txt  # memory (--memory-profile)
```

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--profile` | off | Enable pyinstrument CPU profiling for the parent process. |
| `--profile-workers` | off | Also profile each `multiprocessing` worker; one report per PID. Requires `--profile`. |
| `--profile-serial` | off | Run target compilation serially in the parent (no Pool). Produces a single unified flame graph with full depth. See *Why am I only seeing `IMapUnorderedIterator.next`?* below. |
| `--profile-format` | `html` | One of `html`, `text`, `json`, `speedscope`. |
| `--profile-interval` | `0.001` | pyinstrument sampling interval (seconds). Lower = more detail, more overhead. |
| `--profile-output-dir` | `kapitan-profiles` | Directory to write reports into (created if missing). |
| `--memory-profile` | off | Enable `tracemalloc` snapshot diff; writes a top-N allocation report. |
| `--memory-profile-top` | `30` | Number of top allocators to include. |

The flags are global (registered on the top-level parser), so they go
*before* the subcommand:

```bash
kapitan --profile compile -t my-target     # ✅
kapitan compile --profile -t my-target     # ❌ (argparse error)
```

## Choosing an output format

- **html** (default) — interactive flame-graph-style report, open in any
  browser. Best for exploration.
- **speedscope** — drop the file into <https://www.speedscope.app/>.
- **json** — machine-readable for custom dashboards / CI diffing.
- **text** — printed to stderr *and* written to disk; great for CI logs and
  quick `grep`.

## Why am I only seeing `IMapUnorderedIterator.next`?

`pyinstrument` is a sampling profiler — it can only observe the **current
Python process**. `kapitan compile` farms target compilation out to a
`multiprocessing.Pool`, so the parent process spends almost all its time
blocked in `IMapUnorderedIterator.next` waiting for child results. The
interesting work (kadet, jinja, jsonnet, kustomize, helm…) happens in
separate child processes whose stacks the parent's profiler physically
cannot see.

You have two ways to see deeper:

### Option A — `--profile-workers` (production-shaped)

Keeps the multiprocessing pool. Each worker self-profiles and writes its
own report. Best for understanding real-world behaviour and per-target
variance.

```bash
kapitan --profile --profile-workers compile
```

Load the resulting `kapitan-worker-*.speedscope.json` files into
<https://www.speedscope.app/> (it accepts multiple profiles in tabs).

### Option B — `--profile-serial` (single unified flame graph)

Bypasses the Pool entirely and runs every target's compilation inline in
the parent process. The single pyinstrument report then contains the
**full call tree** including all input-type internals.

```bash
kapitan --profile --profile-serial compile
```

Use this when you're answering "where is time being spent?" — it's the
clearest possible view. Trade-off: wall-clock is slower (no parallelism)
and peak memory is higher (everything runs in one process). Don't use it
for production benchmarking.

> Tip: combine `--profile-serial` with `--profile-format speedscope` and
> the resulting JSON loads into speedscope.app as a single deep flame graph.

## Profiling multiprocessing workers

`kapitan compile` parallelises target compilation with a `multiprocessing.Pool`.
The parent profile shows dispatch/IO/serial work, but **the actual compile
work happens in workers**. Use `--profile-workers` to profile them too:

```bash
kapitan --profile --profile-workers compile
```

Each worker writes its own `kapitan-worker-<ts>-pid<PID>.<ext>` file. To get a
unified view, you can convert the speedscope JSONs and load them as separate
profiles in <https://www.speedscope.app/> (it supports multi-profile views).

Worker profiling is wired via inherited environment variables, so it works
with all `--mp-method` choices (`spawn`, `fork`, `forkserver`).

## Memory profiling notes

`pyinstrument` is a **CPU sampling profiler — it does not measure memory**.
The `--memory-profile` flag uses Python's standard `tracemalloc` to take
snapshots before and after the run and report the top allocation deltas.
The text report includes:

- current allocated bytes at end of run
- peak allocated bytes during the run
- the top *N* allocation sites with full traceback

For deeper memory analysis (allocation timelines, native allocations, leak
detection across long-running processes) consider running Kapitan under
[`memray`](https://bloomberg.github.io/memray/) externally:

```bash
memray run -o kapitan.bin -m kapitan compile
memray flamegraph kapitan.bin
```

## Overhead

- pyinstrument at the default `0.001 s` interval typically adds **<5 %**
  wall-clock overhead.
- `tracemalloc` overhead is much higher (10–50 %) because every allocation is
  intercepted. Only enable `--memory-profile` when you need it.

## CI usage

Profiles are deterministic per-PID-and-timestamp filenames, so it's safe to
upload `kapitan-profiles/` as a CI artifact. Example GitHub Actions step:

```yaml
- name: Compile with profile
  run: kapitan --profile --profile-format speedscope compile

- name: Upload profile
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: kapitan-profile
    path: kapitan-profiles/
```
