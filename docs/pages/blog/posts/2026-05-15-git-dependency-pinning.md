---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 4m
date: 2026-05-15
title: "Pinning Git Dependencies for Reproducible Builds"
description: "How Kapitan pins git dependencies to a tag or commit SHA so your compiled output stops drifting when an upstream branch moves."
---

# :kapitan-logo: **Pinning Git Dependencies for Reproducible Builds**

We've all been there: a compile that worked yesterday produces a slightly different diff today, and nobody touched the inventory. The usual culprit is a git dependency tracking a branch that quietly moved underneath you. Same `kapitan compile`, different output, zero changes on your side.

Git dependencies can now be pinned to a specific tag or commit SHA, not just a branch. That one detail is what turns "it compiled fine on my machine" into a build you can actually reproduce six months from now.

<!-- more -->

## The field you want is `ref`

Git dependencies live under `kapitan.dependencies` in your inventory. The knob we care about is `ref`, and it accepts any value git can resolve: a branch name, a tag, or a full/short commit SHA.

```yaml
parameters:
  kapitan:
    dependencies:
    - type: git
      output_path: source/kapitan
      source: git@github.com:kapicorp/kapitan.git
      subdir: kapitan
      ref: v0.36.0      # pin to a tag
      submodules: true
```

Swap `ref: v0.36.0` for a commit SHA when you want to be ruthless about it:

```yaml
      ref: 776eef38      # short SHA works too
```

Both pin you to an exact point in history. A tag is friendlier to read in a review; a commit SHA can't be moved or deleted out from under you the way a tag technically can. Pick your poison based on how much you trust the upstream maintainer.

!!! note "What `ref` resolves to"
    Under the hood Kapitan runs a `git checkout` of whatever you put in `ref`. So anything `git checkout` understands works here, branches included. The reproducibility win comes from choosing a value that *doesn't move* — a tag or a SHA — rather than a branch like `main`.

## What happens if you leave `ref` out

If you omit `ref` entirely, Kapitan no longer assumes `master`. It falls back to the remote's default branch (`origin/HEAD`) and checks that out. Handy when you genuinely want "latest", but it's exactly the drift-prone case we're trying to avoid for anything you care about reproducing.

```yaml
    - type: git
      output_path: source/kapitan
      source: git@github.com:kapicorp/kapitan.git
      # no ref: -> follows the remote's default branch
```

Our advice, learned the boring way: omit `ref` while you're prototyping, pin it before anything ships.

## Fetching it

Kapitan won't download dependencies on its own. You ask for them with `--fetch`:

```shell
kapitan compile -t kapitan-example --fetch
Dependency kapitan: saved to source/kapitan
Rendered inventory (1.41s)
Compiled kapitan-example (0.83s)
```

`--fetch` only downloads what isn't already on disk. If you change `ref` and want Kapitan to re-pull over an existing checkout, reach for `--force-fetch` instead — by default Kapitan refuses to clobber local files so it doesn't eat your changes.

```shell
kapitan compile -t kapitan-example --force-fetch
```

If you'd rather not type the flag every time, set it in your `.kapitan` dotfile:

```yaml
compile:
  fetch: true
```

## Why we bothered

The reproducibility story is the headline, but pinning pays off in a few quieter ways too. Your diffs get honest — a change in compiled output now means an *intentional* change to a `ref`, not background noise. Rollbacks become a one-line edit. And anyone reading the inventory can see exactly which version of an upstream component you're standing on, without cloning anything.

!!! tip "Pin in CI, float in dev"
    A pattern we like: pin `ref` to a tag in the inventory that CI compiles, and keep a developer overlay that drops the `ref` for fast local iteration. You get reproducible pipelines and a quick inner loop without maintaining two sources of truth for the URL.

Nothing here is exotic. It's one field doing one job well — and that's usually the kind of feature that saves you a confusing afternoon down the line.
