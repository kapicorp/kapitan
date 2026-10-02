---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 5m
date: 2026-05-25
title: "Profiling Slow Kapitan Compiles, Step by Step"
description: "Kapitan can now emit CPU and memory profiles so you can find which target, input, or inventory step is eating your compile time."
---

# :kapitan-logo: **Profiling Slow Kapitan Compiles**

"Why is `kapitan compile` so slow?" is a question we've answered with shrugs and `time` for too long. So we wired actual profilers into Kapitan. You can now ask it to emit a CPU flame graph or a memory report and see, with no guessing, which target or input type is hogging the run.

This is the short tour: the flags, what files you get, and the one gotcha that trips everyone up the first time.

<!-- more -->

## Turn it on

CPU profiling uses [`pyinstrument`](https://github.com/joerick/pyinstrument), which is an optional dependency. Memory profiling leans on the standard-library `tracemalloc`, so it needs nothing extra.

```bash
# install the optional CPU profiler
pip install 'kapitan[profile]'

# CPU profile a compile, write an interactive HTML report
kapitan --profile compile
```

One thing to get right up front: the profiling flags live on the *top-level* parser, so they go **before** the subcommand. Argparse will not forgive you for putting them after.

```bash
kapitan --profile compile -t my-target     # ✅
kapitan compile --profile -t my-target     # ❌ argparse error
```

By default the reports land in `./kapitan-profiles/`, one file per run and (if you ask) per worker PID:

```
kapitan-profiles/
├── kapitan-compile-20260508-101502-pid12345.html        # parent CPU
├── kapitan-worker-20260508-101503-pid12346.html         # worker CPU (--profile-workers)
└── kapitan-compile-20260508-101502-pid12345.memory.txt  # memory (--memory-profile)
```

## The gotcha: where did all my time go?

Here's the moment that confuses everyone. You run `kapitan --profile compile`, open the report, and almost all the time is sitting in something called `IMapUnorderedIterator.next`. Where's your kadet code? Your jinja templates? Nowhere to be seen.

That's not a bug. `pyinstrument` is a sampling profiler and it can only watch the *current* process. But `kapitan compile` farms each target out to a `multiprocessing.Pool`, so the parent process spends its life blocked, waiting for children. The actual work, the part you care about, runs in separate worker processes the parent's profiler physically cannot see.

There are two ways through this, and they answer different questions.

### `--profile-serial` when you want the full picture

If your question is simply "where is time being spent?", this is the clearest view. It skips the Pool entirely and compiles every target inline in the parent process, so the single report contains the whole call tree, input-type internals and all.

```bash
kapitan --profile --profile-serial compile
```

The trade-off is honest: wall-clock is slower because there's no parallelism, and peak memory is higher because everything runs in one process. Don't reach for it when you're benchmarking production timings, reach for it when you're hunting.

### `--profile-workers` when you want real behaviour

This keeps the multiprocessing pool intact. Each worker self-profiles and writes its own per-PID report, which is what you want for understanding real-world behaviour and per-target variance.

```bash
kapitan --profile --profile-workers compile
```

!!! note "Worker profiling and `--mp-method`"
    Worker profiling is wired through inherited environment variables, so it works across all `--mp-method` choices: `spawn`, `fork`, and `forkserver`.

## Picking a format

The default is `html`, but `--profile-format` takes four values and they suit different jobs:

| Format | Good for |
|---|---|
| `html` | Interactive flame-graph report in a browser. Best for poking around. |
| `speedscope` | Drop the file into [speedscope.app](https://www.speedscope.app/); it can load several worker profiles in tabs. |
| `json` | Machine-readable, for CI diffing or your own dashboards. |
| `text` | Printed to stderr *and* written to disk. Great for CI logs and a quick `grep`. |

Our favourite combination for a deep single view is serial mode plus speedscope:

```bash
kapitan --profile --profile-serial --profile-format speedscope compile
```

If the sampling feels too coarse, `--profile-interval` defaults to `0.001` seconds. Lower it for more detail at the cost of more overhead.

## Memory, separately

`pyinstrument` measures CPU, not memory, so memory gets its own flag. `--memory-profile` takes a `tracemalloc` snapshot before and after the run and writes the top allocation deltas to a text file.

```bash
kapitan --profile --memory-profile compile
```

The report opens with the headline numbers and then the worst allocation sites, each with a full traceback:

```
Kapitan memory profile (tracemalloc)
  current allocations at end of run: 84.21 MiB
  peak allocations during run:       312.07 MiB
  top 30 allocation deltas:

#1: .../inputs/kadet.py:142: size=18.4 MiB, count=21034
    ...
```

`--memory-profile-top` controls how many sites you get (30 by default). Fair warning on overhead: `pyinstrument` at the default interval usually adds under 5% wall-clock, but `tracemalloc` intercepts every allocation and can add 10–50%. Only switch on `--memory-profile` when you actually need it.

## In CI

The filenames are keyed on subcommand, timestamp, and PID, so it's safe to upload the whole directory as an artifact:

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

That's the whole feature. The full reference, including notes on running Kapitan under [`memray`](https://bloomberg.github.io/memray/) for deeper memory work, lives in [Profiling Kapitan runs](../../profiling.md). Next time someone asks why a compile is slow, you can answer with a flame graph instead of a shrug.
