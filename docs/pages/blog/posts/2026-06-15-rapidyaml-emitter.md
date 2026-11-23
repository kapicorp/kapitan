---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 3m
date: 2026-06-15
title: "Faster YAML Output with the rapidyaml Emitter"
description: "Speed up YAML-heavy Kapitan compiles with the optional rapidyaml emitter: how to enable it, what it costs, and a real benchmark."
---

# Faster YAML Output with the rapidyaml Emitter

In compiles that produce a lot of Kubernetes manifests, a large share of the
wall-clock time is not templating or inventory rendering. It is the YAML
emitter: PyYAML passes every node through a chain of Python callbacks to
turn dicts back into text.

Since v0.36.0, Kapitan has an opt-in alternative: the C++ emitter
[rapidyaml](https://github.com/biojppm/rapidyaml), enabled with a single
flag. Without the flag, nothing changes.

<!-- more -->

## Enabling it

The emitter is an optional extra, so installs that do not need a native YAML
library do not carry it. Install the extra and pass the flag:

```shell
pip install kapitan[rapidyaml]
kapitan compile --yaml-use-rapidyaml
```

The extra is named `rapidyaml`, but the Python module it installs is
imported as `ryml`.

To enable it permanently, set it in the `compile` section of `.kapitan`:

```yaml
# .kapitan
compile:
  yaml-use-rapidyaml: true
```

If the flag is set but the extra is not installed, the compile does not
fail. Kapitan logs a one-time warning and uses PyYAML.

## Speed

On a realistic Kubernetes Deployment manifest, the rapidyaml emitter is
about 6x faster than the PyYAML path. For whole compiles there is one data
point so far: in the pull request that added the emitter
([#1464](https://github.com/kapicorp/kapitan/pull/1464)), its author reports
that local tests on a large codebase compiled about three times faster. The
emitter is only one part of a compile, so the gain depends on
how much of your compile time is spent writing YAML.

The difference comes from the approach. PyYAML runs every scalar and
collection through Python representer and emitter callbacks; rapidyaml
builds a contiguous tree in C++ and emits from that.

## Output is not byte-identical

Test this before enabling it in CI. The output is semantically equivalent
to PyYAML's: keys are still sorted alphabetically, and every scalar loads
back to the same Python value. The text may differ cosmetically, depending
on the rapidyaml version. With 0.12.1, the version in Kapitan's `uv.lock`,
rapidyaml single-quotes a scalar such as `mysql:latest` that PyYAML leaves
plain. rapidyaml 0.15.2 writes it plain, like PyYAML.

```yaml
# PyYAML, and rapidyaml 0.15.2
image: mysql:latest
# rapidyaml 0.12.1
image: 'mysql:latest'
```

Both load as the same string. Tests or fixtures that compare compiled output
byte for byte will show a diff on the first compile and need regenerating.

The flag applies to a whole run. To roll it out gradually, use it for
separate runs over the targets with the largest manifests (`-t`), or locally
for faster iteration, and keep CI on PyYAML until the golden files are
regenerated.

One more fallback is built in: output containing ASCII control characters
is written by PyYAML, because rapidyaml does not escape them in
double-quoted scalars. Kapitan makes that switch per output file, with no
configuration.

## When to use it

For small compiles the default emitter is fine. If you compile large
manifests or hundreds of targets and writing YAML is a visible share of the
build time, install the extra, regenerate byte-exact fixtures once, and
switch it on. The flag is documented with the other options of
[`kapitan compile`](../../commands/kapitan_compile.md#fast-yaml-emission-with-rapidyaml).
