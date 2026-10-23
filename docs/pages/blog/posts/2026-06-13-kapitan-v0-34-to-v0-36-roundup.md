---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 4m
date: 2026-06-13
title: "What's New in Kapitan from v0.34 to v0.36"
description: "A roundup of headline Kapitan features from v0.34 to v0.36: wildcard classes, OCI generators, OmegaConf, profiling, and more."
---

# What's New in Kapitan from v0.34 to v0.36

v0.36.0 is out. The last release covered on this blog was v0.33.1, so this
post goes back to v0.34 and lists the headline changes since, each with a
pointer to its documentation and pull request. Most of the features below
first shipped in v0.36.0.

<!-- more -->

## Wildcard class patterns

`classes:` entries can be glob patterns. `clusters.*` expands to every class
whose dotted name starts with `clusters.`, and `"*"` (quoted, because a bare
`*` is not valid YAML here) to every class. Patterns match the full dotted
name, so `dev-*` only matches top-level classes; use `*.dev-*` for nested
ones.

```yaml
classes:
  - common
  - clusters.*
```

Expansion is off by default. Enable it with `--enable-class-wildcards` or
`enable-class-wildcards: true` under `inventory_backend` in `.kapitan`. The
patterns are expanded before the backend reads the inventory, so reclass,
reclass-rs and OmegaConf behave the same.
[Docs](../../inventory/classes.md#wildcard-class-patterns),
[#1457](https://github.com/kapicorp/kapitan/pull/1457).

## Generators as OCI artifacts

The new `oci` dependency type pulls a generator bundle from an OCI registry
such as GHCR, Docker Hub or Harbor, by tag or by digest:

```yaml
parameters:
  kapitan:
    dependencies:
    - type: oci
      source: ghcr.io/<org>/<generator>:1.2.0
      output_path: components/generators
```

It requires the optional extra `pip install kapitan[oci]`, and bundles are
published with the `oras` CLI.
[Docs](../../publishing_generators.md),
[#1425](https://github.com/kapicorp/kapitan/pull/1425).

## OmegaConf backend

The OmegaConf backend, experimental since v0.34, gained two fixes. The
`${escape:...}` resolver emits a literal `${...}` into the compiled output,
for Terraform references or shell variables that must not be resolved as
inventory keys (v0.35.1,
[#1445](https://github.com/kapicorp/kapitan/pull/1445)). And v0.36.0 makes
`--migrate` run before the backend loads the inventory, raises migration
errors instead of swallowing them, and lets the backend find class files
with the `.yaml` extension
([#1483](https://github.com/kapicorp/kapitan/pull/1483)).
[Docs](../../inventory/omegaconf.md).

## Pinning git dependencies

The `ref` of a git dependency accepts a branch, a tag, or a full or short
commit SHA. Without `ref`, Kapitan now checks out the remote's default
branch instead of assuming `master`.

```yaml
- type: git
  source: https://github.com/example/repo.git
  ref: v1.0.0
```

Pin a tag or SHA for reproducible fetches.
[Docs](../../external_dependencies.md),
[#1451](https://github.com/kapicorp/kapitan/pull/1451).

## CPU and memory profiling

`--profile` wraps the run in the
[pyinstrument](https://github.com/joerick/pyinstrument) CPU profiler and
writes a report. `--profile-workers` adds one report per compile worker,
where most of the compile time is spent, and `--memory-profile` writes a
`tracemalloc` report. The flags are global and go before the subcommand:

```shell
kapitan --profile --profile-workers compile
```

CPU profiling requires `pip install kapitan[profile]`.
[Docs](../../profiling.md),
[#1507](https://github.com/kapicorp/kapitan/pull/1507).

## Topics

Topics let a target publish selected parameters under
`parameters.kapitan.topics.<name>.parameters`. Kapitan aggregates all
publishers of a topic into one view, which other targets read with the
`topics()` function in Kadet, Jinja2 and Jsonnet. Since v0.36.2, released
after this post, a reading target must also declare `consume: true` on the
topic.
[Docs](../../inventory/advanced.md),
[#1466](https://github.com/kapicorp/kapitan/pull/1466).

## rapidyaml emitter

`--yaml-use-rapidyaml` replaces PyYAML with the C++ emitter
[rapidyaml](https://github.com/biojppm/rapidyaml). On a large codebase the
author of the change measured compile times dropping by about 3x. The
output is semantically equivalent but not byte-identical to PyYAML's, so
fixtures that compare exact bytes need regenerating. Without the
`kapitan[rapidyaml]` extra, Kapitan warns once and uses PyYAML.
[Docs](../../commands/kapitan_compile.md#fast-yaml-emission-with-rapidyaml),
[#1464](https://github.com/kapicorp/kapitan/pull/1464).

## mise for contributor tooling

The external binaries the test suite needs, helm, kustomize and cue, are now
installed and pinned with [mise](https://mise.jdx.dev/) through `mise.toml`
and `mise.lock`, while `uv` keeps managing Python. Local setup and CI
install the same versions. This only affects working on Kapitan itself.
[#1411](https://github.com/kapicorp/kapitan/pull/1411).

## Other changes

v0.34 added the experimental reclass-rs and OmegaConf backends,
Pydantic-based inventory validation, and Python 3.12 support. v0.35 added
Python 3.13 and 3.14, moved the project to `uv` and Ruff, and introduced the
Kadet input cache. The full lists, and the contributors behind them, are on
the release pages for
[v0.34.0](https://github.com/kapicorp/kapitan/releases/tag/v0.34.0),
[v0.35.0](https://github.com/kapicorp/kapitan/releases/tag/v0.35.0) and
[v0.36.0](https://github.com/kapicorp/kapitan/releases/tag/v0.36.0).

If Kapitan is useful to you, consider
[sponsoring the project](../../contribute/sponsor.md).
