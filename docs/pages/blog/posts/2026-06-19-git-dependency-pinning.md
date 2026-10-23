---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 3m
date: 2026-06-19
title: "Pinning Git Dependencies for Reproducible Builds"
description: "How Kapitan pins git dependencies to a tag or commit SHA so your compiled output stops drifting when an upstream branch moves."
---

# Pinning Git Dependencies for Reproducible Builds

A compile that produced one diff yesterday produces a different one today,
and nobody touched the inventory. The usual cause is a git dependency that
tracks a branch, and the branch moved upstream.

Git dependencies can be pinned to a tag or a commit SHA, not only a branch.
v0.36.0 documents and tests this, and changes what happens when no `ref` is
set at all.

<!-- more -->

## The `ref` field

Git dependencies live under `kapitan.dependencies`. `ref` takes any value
`git checkout` accepts: a branch, a tag, or a full or short commit SHA.

```yaml
parameters:
  kapitan:
    dependencies:
    - type: git
      output_path: source/kapitan
      source: https://github.com/kapicorp/kapitan.git
      subdir: kapitan
      ref: v0.36.0      # pin to a tag
      submodules: true
```

or with a commit:

```yaml
      ref: 776eef38      # short SHA
```

Kapitan clones the full repository and runs `git checkout` with the value of
`ref`, so branches work too. Reproducibility comes from choosing a value that
does not move. A tag reads better in review; a commit SHA cannot be moved or
deleted upstream the way a tag can.

## Without `ref`

If `ref` is omitted, Kapitan no longer assumes `master`. It checks out the
remote's default branch, as `git clone` reports it. That is convenient while
prototyping and is exactly the drift-prone case for anything you want to
reproduce later.

```yaml
    - type: git
      output_path: source/kapitan
      source: https://github.com/kapicorp/kapitan.git
      # no ref: follows the remote's default branch
```

## Fetching

Dependencies are fetched when you pass `--fetch`, or for individual
dependencies that set `force_fetch: true` in the inventory:

```shell
$ kapitan compile -t kapitan-example --fetch
Rendered inventory (0.00s): discovered 1 targets.
Compiling 1/1 targets using 1 concurrent processes: (24 CPU available)
Dependency https://github.com/kapicorp/kapitan.git: saved to source/kapitan
Fetched dependencies (6.06s)
Compiled kapitan-example (0.00s)
Compiled 1 targets in 0.49s
```

`--fetch` clones the repository again on every run, but it does not
overwrite files that already exist in `output_path`. After changing `ref`,
use `--force-fetch` so the checkout at the new ref replaces the old files:

```shell
kapitan compile -t kapitan-example --force-fetch
```

To fetch on every compile without the flag, set it in `.kapitan`:

```yaml
compile:
  fetch: true
```

## What pinning buys

A change in compiled output now traces back to a change of `ref` in the
inventory, rather than to an upstream commit you did not review. Rolling
back is a one-line edit, and the inventory states which upstream version
each target is built from.

To track a branch locally while CI builds a pinned version, put the ref in a
parameter, `ref: ${upstream_ref}`, and set `upstream_ref` to a tag in a
common class. A developer overlay class then overrides `upstream_ref` with a
branch name. The dependency itself is still defined once. Redefining the
entry in the overlay's `dependencies` list does not work, because lists from
several classes are appended and the target ends up with both entries.

The field reference is in
[External dependencies](../../external_dependencies.md).
