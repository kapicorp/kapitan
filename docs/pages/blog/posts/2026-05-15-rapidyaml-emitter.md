---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 4m
date: 2026-05-15
title: "Faster YAML Output with the rapidyaml Emitter"
description: "Speed up YAML-heavy Kapitan compiles with the optional rapidyaml emitter: how to enable it, what it costs, and a real benchmark."
---

# :kapitan-logo: **Faster YAML output with the rapidyaml emitter**

If you compile a lot of Kubernetes manifests, you've probably watched Kapitan
sit there churning. A surprising chunk of that wall-clock time isn't templating
or inventory rendering at all, it's the YAML emitter, PyYAML walking every node
through a chain of Python callbacks to turn your dicts back into text.

We added an opt-in fast path for exactly this. It's a C++ YAML emitter called
[rapidyaml](https://github.com/biojppm/rapidyaml), wired in behind a single
flag. It's off by default, so nothing changes unless you ask for it.

<!-- more -->

## Turning it on

The emitter lives in an optional extra, because most installs don't need a
native YAML library and we didn't want to make everyone carry the wheel. Two
steps: install the extra, then pass the flag.

```shell
pip install kapitan[rapidyaml]
kapitan compile --yaml-use-rapidyaml
```

One wrinkle worth knowing up front: the extra is named `rapidyaml` but the
Python module it ships is imported as `ryml`. You'll only notice if you go
poking at it directly.

If you'd rather not type the flag on every invocation, set it in your `.kapitan`
file under the `compile` section:

```yaml
# .kapitan
compile:
  yaml-use-rapidyaml: true
```

!!! note "It fails soft"
    If you pass `--yaml-use-rapidyaml` but never installed the extra, Kapitan
    doesn't error out. It logs a one-time warning and quietly falls back to
    PyYAML, so a missing dependency degrades to "the old behaviour" rather than
    a broken compile.

## What you get

In our own testing on a realistic Kubernetes Deployment manifest, the rapidyaml
emitter came out around **6x faster** than the default PyYAML path. On a large
real-world codebase, the author of the change measured end-to-end compile times
dropping by roughly a factor of three, the emitter isn't the only cost in a
compile, so your mileage depends on how YAML-bound your targets are.

The win is structural. PyYAML streams every scalar and collection through Python
representer and emitter callbacks; rapidyaml builds a contiguous tree buffer in
C++ and emits from that. The more manifests you're dumping, the more that
difference adds up.

## The honest part: output isn't byte-identical

This is the tradeoff, and it's the thing to test before you flip it on in CI.

The output is **semantically equivalent** to PyYAML's: keys are still sorted
alphabetically, and every scalar round-trips back to the same Python object. But
it isn't always byte-for-byte the same text. The most common difference is
quoting, rapidyaml may single-quote a scalar that PyYAML left plain, for
example:

```yaml
# PyYAML
image: mysql:latest
# rapidyaml
image: 'mysql:latest'
```

Both parse to the identical string. But if you have tests or fixtures that
compare compiled output byte-for-byte, that first compile will look like a diff,
and you'll need to regenerate those fixtures.

!!! tip "Roll it out where it pays off"
    Because the flag is per-invocation, you don't have to commit globally. Turn
    it on for the targets with the heaviest manifests and leave the rest alone,
    or enable it locally for fast iteration and keep CI on the default emitter
    until you've regenerated your golden files.

There's one more fallback baked in: if a document contains ASCII control
characters, that single document is emitted by PyYAML instead, because rapidyaml
doesn't escape those in double-quoted scalars. You don't have to do anything,
Kapitan handles the switch per-document.

## Should you use it?

If your compiles are small, the default PyYAML emitter is fine and you can
ignore all of this. If you're compiling big manifests or hundreds of targets and
the YAML step is a real share of your build time, install the extra, regenerate
any byte-exact fixtures once, and enjoy the faster path. It's opt-in precisely
so you only take on the tradeoff when the speed is worth it.
