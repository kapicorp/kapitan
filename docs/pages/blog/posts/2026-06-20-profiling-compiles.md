---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 4m
date: 2026-06-20
title: "Profiling Slow Kapitan Compiles, Step by Step"
description: "Kapitan can now emit CPU and memory profiles so you can find which target, input, or inventory step is eating your compile time."
---

# Profiling Slow Kapitan Compiles, Step by Step

"Why is `kapitan compile` slow?" used to be answered with `time` and
guesswork. Since v0.36.0, Kapitan can write a CPU profile or a memory report
for any run, so you can see which target or input type takes the time.

This post covers the flags, the files they produce, and the one result that
confuses almost everyone the first time.

<!-- more -->

## Enabling it

CPU profiling uses [`pyinstrument`](https://github.com/joerick/pyinstrument),
an optional extra. Memory profiling uses the standard library's
`tracemalloc` and needs nothing extra.

```bash
pip install 'kapitan[profile]'

# CPU profile a compile, write an interactive HTML report
kapitan --profile compile
```

The profiling flags belong to the top-level parser, so they go before the
subcommand. After it, argparse rejects them:

```bash
kapitan --profile compile -t my-target     # works
kapitan compile --profile -t my-target     # argparse error
```

Reports are written to `./kapitan-profiles/` unless you pass
`--profile-output-dir`. File names contain the subcommand, a UTC timestamp
and the process ID:

```
kapitan-profiles/
├── kapitan-compile-20260508-101502-pid12345.html        # parent CPU
├── kapitan-worker-20260508-101503-pid12346.html         # worker CPU (--profile-workers)
└── kapitan-compile-20260508-101502-pid12345.memory.txt  # memory (--memory-profile)
```

## Where did the time go?

The first report from `kapitan --profile compile` usually shows nearly all
the time in `IMapUnorderedIterator.next`, and none of your Kadet code or
Jinja2 templates.

That is expected. `pyinstrument` samples only the process it runs in, and
`kapitan compile` hands each target to a `multiprocessing.Pool`. The parent
process spends the run waiting for its workers, and the actual compile work
happens in worker processes the parent's profiler cannot see. There are two
ways around it, answering different questions.

`--profile-serial` compiles every target in the parent process without a
pool, so a single report contains the full call tree, including input type
internals. Wall-clock time is longer because nothing runs in parallel, and
peak memory is higher because everything shares one process. Use it to find
where time goes, not to measure production timings.

```bash
kapitan --profile --profile-serial compile
```

`--profile-workers` keeps the pool. Each worker profiles itself and writes
its own report per PID, which shows real-world behaviour and the variance
between targets. It requires `--profile` and has no effect without it.
Worker profiling is passed to workers through environment variables, so it
works with every `--mp-method`: `spawn`, `fork` and `forkserver`.

```bash
kapitan --profile --profile-workers compile
```

## Output formats

`--profile-format` defaults to `html` and takes four values:

| Format | Use |
|---|---|
| `html` | Interactive report in the browser. |
| `speedscope` | `.speedscope.json` for [speedscope.app](https://www.speedscope.app/), which can open several worker profiles as tabs. |
| `json` | Machine-readable, for diffing in CI or your own tooling. |
| `text` | Written to disk and printed to stderr, useful in CI logs. |

For a single detailed view, serial mode with speedscope works well:

```bash
kapitan --profile --profile-serial --profile-format speedscope compile
```

`--profile-interval` sets the sampling interval and defaults to `0.001`
seconds. A lower value gives more detail and more overhead.

## Memory

`pyinstrument` measures CPU time only. `--memory-profile` takes a
`tracemalloc` snapshot before and after the run and writes the largest
allocation deltas to a text file. `tracemalloc` runs in the parent process
only, so allocations made inside compile workers show up only together with
`--profile-serial`:

```bash
kapitan --profile --profile-serial --memory-profile compile
```

The report starts with totals, followed by the top allocation sites with
tracebacks:

```
Kapitan memory profile (tracemalloc)
  current allocations at end of run: 84.21 MiB
  peak allocations during run:       312.07 MiB
  top 30 allocation deltas:

#1: .../inputs/kadet.py:142: size=18.4 MiB, count=21034
    ...
```

`--memory-profile-top` sets the number of sites and defaults to 30.
`tracemalloc` hooks every allocation and slows the run down noticeably more
than `pyinstrument` does, so turn it on only when you need it.

## In CI

File names include subcommand, timestamp and PID, so the whole directory can
be uploaded as an artifact without collisions:

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

The full reference, including notes on running Kapitan under
[`memray`](https://bloomberg.github.io/memray/) for deeper memory analysis,
is in [Profiling Kapitan runs](../../profiling.md).
