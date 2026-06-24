---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 6m
date: 2026-06-12
title: "What's New in Kapitan from v0.34 to v0.36"
description: "A roundup of headline Kapitan features from v0.34 to v0.36: wildcard classes, OCI generators, OmegaConf, profiling, and more."
---

# :kapitan-logo: **What's new from v0.34 to v0.36**

The last time we posted here was February 2024, for the v0.33.1 release. Then the blog went quiet. The code did not — three releases shipped in the meantime, plus a long tail of point releases. So this is us catching up, honestly: a single signpost covering the headline changes from v0.34 through v0.36, with a pointer into each one rather than a deep dive.

If you only read one paragraph: inventories got faster and more flexible, generators can now travel as OCI artifacts, and there are some sharp new tools for when a compile feels slow.

<!-- more -->

## Wildcard class patterns

You can now put glob patterns in your `classes:` lists. `clusters.*` expands to every matching class under `inventory/classes/`, `dev-*` matches by basename in any subdir, and `"*"` (quote it, or YAML gets confused) pulls in everything.

```yaml
classes:
  - common
  - clusters.*
```

It's off by default — enable it with `--enable-class-wildcards` or in your `.kapitan`. The expansion happens before the backend ever sees it, so reclass, reclass-rs, and OmegaConf all behave the same way. ([#1457](https://github.com/kapicorp/kapitan/pull/1457))

## Sharing generators as OCI artifacts

There's a new `oci` dependency type. Point it at a registry — GHCR, Docker Hub, a private Harbor — and Kapitan pulls a generator bundle the same way you'd pull a container image, digest pinning and all.

```yaml
parameters:
  kapitan:
    dependencies:
    - type: oci
      source: ghcr.io/kapicorp/generators:1.2.0
      output_path: components/generators
```

It rides on `oras`, which is an optional extra (`pip install kapitan[oci]`). ([#1425](https://github.com/kapicorp/kapitan/pull/1425))

## OmegaConf backend improvements

The OmegaConf inventory backend, which landed experimentally in v0.34, kept growing. Two things worth calling out: the `${escape:...}` resolver now emits a literal `${...}` into your compiled output — handy when you want a Terraform reference or a shell variable to survive untouched instead of being resolved as an inventory key ([#1445](https://github.com/kapicorp/kapitan/pull/1445)). And `--migrate` now actually works end to end, including `.yaml` class files, which it used to silently skip ([#1483](https://github.com/kapicorp/kapitan/pull/1483)).

## Pinning git dependencies to a tag or SHA

The `ref` field on git dependencies accepts any git-resolvable value — a branch, a tag, or a commit SHA. That was always half-true; now it's documented, guarded against a `None` ref, and tested.

```yaml
- type: git
  source: https://github.com/example/repo.git
  ref: v1.0.0
```

Pin to a tag or full SHA when you want reproducible fetches. ([#1451](https://github.com/kapicorp/kapitan/pull/1451))

## CPU and memory profiling

When a compile feels slow, you no longer have to guess. `--profile` wraps the run in a [pyinstrument](https://github.com/joerick/pyinstrument) CPU profiler and writes a report; `--profile-workers` extends that into the multiprocessing workers, where the real compile time usually hides. Memory profiling uses `tracemalloc`.

```shell
kapitan compile --profile --profile-workers
```

Profiling is an optional extra (`pip install kapitan[profile]`). ([#1507](https://github.com/kapicorp/kapitan/pull/1507))

## Topics

Topics let a target expose a chosen slice of its parameters so other targets can read it. A target opts in under `parameters.kapitan.topics.<name>.parameters`, and Kapitan aggregates every participant into a single view you can query with the `topics()` function.

!!! note
    This is a way to share data across targets without hard-coding one target's internals into another. See the [inventory advanced](../../inventory/advanced.md) docs for the full shape.

([#1466](https://github.com/kapicorp/kapitan/pull/1466))

## mise for external tools

Kapitan leans on a few external binaries — helm, kustomize, cue. We moved their version management to [mise](https://mise.jdx.dev/), pinned in `mise.toml`, while `uv` stays in charge of Python. Local setup and CI now bootstrap tools the same way, which mostly means "works on my machine" arguments got a little shorter.

This is a contributor-facing change rather than something you'll see at compile time. ([#1411](https://github.com/kapicorp/kapitan/pull/1411))

## rapidyaml emitter

A new `--yaml-use-rapidyaml` flag swaps the YAML emitter for [rapidyaml](https://github.com/biojppm/rapidyaml). On a large codebase the author measured compile times dropping by roughly 3x.

!!! tip
    The first compile after switching may show formatting differences against PyYAML output — semantically equivalent, just emitted differently. It falls back to PyYAML if rapidyaml isn't installed.

([#1464](https://github.com/kapicorp/kapitan/pull/1464))

## And the rest

A lot of the work in this window wasn't a single headline feature. v0.34 brought the experimental reclass-rs and OmegaConf backends, Pydantic-based inventory validation, and Python 3.12. v0.35 added Python 3.13 (and 3.14), moved the project to `uv` and Ruff, and introduced a Kadet input cache. For the full list — and the contributors behind it, many from the community — head to the release pages for [v0.34.0](https://github.com/kapicorp/kapitan/releases/tag/v0.34.0), [v0.35.0](https://github.com/kapicorp/kapitan/releases/tag/v0.35.0), and [v0.36.0](https://github.com/kapicorp/kapitan/releases/tag/v0.36.0).

If you find Kapitan useful, the [Sponsor Kapitan](../../contribute/sponsor.md) page is the kindest way to say so.
