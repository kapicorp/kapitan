---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 5m
date: 2026-06-22
title: "Expanding Inventory Classes with Wildcard Patterns"
description: "Use --enable-class-wildcards to expand glob patterns like clusters.* in Kapitan inventory classes lists, across every backend."
---

# Expanding Inventory Classes with Wildcard Patterns

Large inventories tend to end up with targets whose `classes:` list runs to
twenty lines. Every new class that half the targets should import means
editing each of those targets, and the one you miss compiles without it.

Since v0.36.0, a `classes:` entry can be a glob pattern. `clusters.*` expands
to every matching class on disk. The feature is opt-in and works the same
under reclass, reclass-rs and OmegaConf.

<!-- more -->

## Before and after

A target that lists each cluster class explicitly:

```yaml
# inventory/targets/all-clusters.yml
classes:
  - common
  - clusters.dev
  - clusters.staging
  - clusters.prod
```

Add `classes/clusters/canary.yml` and this target is out of date. With
wildcards enabled, the same target becomes:

```yaml
# inventory/targets/all-clusters.yml
classes:
  - common
  - clusters.*
```

`clusters.*` expands, in place, to every class whose dotted name starts with
`clusters.`, sorted lexicographically. `common` is an exact name and passes
through unchanged.

## Turning it on

Wildcard expansion is disabled by default. Some inventories have glob
metacharacters in class names for legitimate reasons, such as a file named
`config[html].yml` or a reclass reference like `${?optional_param}`, and
those must not be reinterpreted silently. Enable it per run:

```shell
kapitan inventory --enable-class-wildcards -t all-clusters
```

or permanently in `.kapitan`, under the inventory backend section:

```yaml
# .kapitan
inventory_backend:
  enable-class-wildcards: true
```

The flag is accepted by `kapitan compile`, `kapitan inventory` and
`kapitan refs`. `kapitan inventory` is the quickest way to check what a
pattern expands to, since it prints the merged result without writing
anything to `compiled/`.

## Pattern semantics

Patterns are matched against the full dotted class name with Python's
[`fnmatch`](https://docs.python.org/3/library/fnmatch.html), so `*`, `?` and
`[ ]` work as usual:

```yaml
classes:
  - "*"             # every class, top-level and nested (quoted: bare * is not valid YAML here)
  - clusters.*      # every class whose dotted name starts with 'clusters.'
  - apps.dev-*      # classes under apps/ whose basename starts with 'dev-'
  - "*.dev-*"       # a 'dev-...' segment in any subdirectory
```

Dots get no special treatment. `dev-*` matches only top-level classes named
`dev-...`; to reach `apps.dev-api` you write `apps.dev-*` or `*.dev-*`. Also
note that `*` crosses dots, so `apps.dev-*` matches `apps.dev-api.v2` as well.

Class names follow the usual mapping: `classes/clusters/prod.yml` is
`clusters.prod`, and `classes/foo/init.yml` collapses to `foo`.

Two rules decide whether an entry is treated as a pattern at all. If a class
with that exact name exists, the entry is an exact include: `- config[html]`
picks up `config[html].yml` and is not read as a character class. And any
entry containing `${` and `}` is handed to the backend verbatim, even with a
`?` inside, because references resolve after class inheritance and the
expander cannot evaluate them. This also means patterns inside a reference
are not expanded.

## Ordering and merge precedence

Each pattern expands to a lexicographically sorted list. Duplicates, whether
from another pattern or an exact entry, are dropped and the first occurrence
is kept.

Sorted order is deterministic, but it can move under you. `*.base` matching
`config.base` and `defaults.base` expands to `[config.base, defaults.base]`.
Add `alpha.base` later and both shift one position down. If merge precedence
matters, name classes so they sort in the order you want:

```yaml
classes:
  - app.00-defaults
  - app.10-config
  - app.90-overrides
```

`app.*` then keeps that order regardless of what gets added. Where merge
order is critical and you do not control the names, list the classes
explicitly.

A pattern that matches nothing raises an inventory error, also when
compiling with `--fetch`.

## How it works

No backend was changed. When the flag is on and at least one `classes:` list
under `inventory/targets/` or `inventory/classes/` contains a pattern,
Kapitan copies the inventory tree to a temporary directory, expands the
patterns in the copy, and points the backend at it. The backend never sees a
wildcard. The copy is removed on exit, and relative symlinks that would break
in the copy are rewritten to absolute paths.

With the flag off, none of this runs and the inventory path is used as is.
With the flag on, a text pre-filter skips YAML parsing for files that contain
no glob metacharacter. Inventories with many AWS ARNs, ref tags or YAML
anchors pass more files through that filter, which then get parsed.

The full reference is in the
[classes documentation](../../inventory/classes.md#wildcard-class-patterns).
