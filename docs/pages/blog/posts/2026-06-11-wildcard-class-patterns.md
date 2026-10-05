---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 5m
date: 2026-06-11
title: "Expanding Inventory Classes with Wildcard Patterns"
description: "Use --enable-class-wildcards to expand glob patterns like clusters.* in Kapitan inventory classes lists, across every backend."
---

# :kapitan-logo: **Expanding Inventory Classes with Wildcard Patterns**

Every large inventory eventually grows the same wart: a target file with a `classes:` list twenty lines long, and a sinking feeling every time someone adds a new class that half the targets should now import. You either update them all by hand or you forget one. We've done both.

So we added wildcards. You can now write `clusters.*` in a `classes:` list and let Kapitan expand it to every matching class on disk. It's opt-in, it works with every inventory backend, and the rest of this post shows exactly how.

<!-- more -->

## The before/after

Here's a target that pins each cluster class explicitly:

```yaml
# inventory/targets/all-clusters.yml
classes:
  - common
  - clusters.dev
  - clusters.staging
  - clusters.prod
```

Add `clusters.canary.yml` next week and this file is silently out of date. With wildcards on, the same target becomes:

```yaml
# inventory/targets/all-clusters.yml
classes:
  - common
  - clusters.*
```

`clusters.*` expands to every class whose dotted name starts with `clusters.`, sorted lexicographically, inserted right where the pattern sits. `common` stays exactly where it is — exact names are passed through untouched.

## Turning it on

Wildcard expansion is **disabled by default**, and on purpose. Plenty of real inventories have glob metacharacters in class names for honest reasons — a file literally called `config[html].yml`, or a Reclass reference like `${?optional_param}`. We didn't want to silently reinterpret those, so you have to ask for it:

```shell
kapitan inventory --enable-class-wildcards -t all-clusters
```

Or, if you'd rather not type it every time, put it in `.kapitan` under the inventory backend section:

```yaml
# .kapitan
inventory_backend:
  enable-class-wildcards: true
```

The flag lives on both `kapitan compile` and `kapitan inventory`, so you can preview the expansion before you compile anything. We find ourselves reaching for `kapitan inventory` first — it shows you the merged result without writing a single file to `compiled/`.

## What the patterns actually mean

The matching rule is deliberately boring. Patterns are matched against the **full dotted class name** with Python's [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) — so `*`, `?`, and `[ ]` all work:

```yaml
classes:
  - "*"             # every class, top-level and nested (quote it — bare * is ambiguous YAML)
  - clusters.*      # every class whose dotted name starts with 'clusters.'
  - apps.dev-*      # classes under apps/ whose basename starts with 'dev-'
  - "*.dev-*"       # a 'dev-...' segment in any subdir
```

There's no clever special-casing for dots. `dev-*` matches only *top-level* classes named `dev-...`; if you want `apps.dev-api`, you write `apps.dev-*` or `*.dev-*`. We went back and forth on this and landed on "no surprises" over "convenient".

!!! note "Class names follow the usual rules"
    A pattern matches the same dotted names you'd write by hand: `classes/clusters/prod.yml` is `clusters.prod`, and `classes/foo/init.yml` collapses to `foo` (the reclass `init` convention). The wildcard expander discovers classes the same way the backend resolves them.

Two behaviors worth knowing:

- **Exact names win over patterns.** If a class file is literally named `config[html].yml`, then `- config[html]` includes that one file as-is. It's only treated as a character-class pattern when no class with that exact name exists.
- **Reclass references pass through.** Anything containing `${` and `}` is handed to the backend verbatim, even with a `?` inside. The expander can't resolve `${...}` — that happens after class inheritance — so it doesn't try.

## Order is deterministic, but mind the merge

Each pattern expands to a **lexicographically sorted** list, and duplicates (across both exact entries and expansions) are dropped, keeping the first occurrence. Deterministic is good. It can also bite you.

!!! tip "Numeric prefixes when merge order matters"
    `*.base` matching `config.base` and `defaults.base` always expands to `[config.base, defaults.base]` because `c < d`. Add `alpha.base` later and the order shifts. If precedence matters to your merge, name classes so they sort the way you want:

    ```yaml
    classes:
      - app.00-defaults
      - app.10-config
      - app.90-overrides
    ```

    `app.*` then expands in the intended order no matter what gets added later. When merge order is critical and you can't control naming, just don't use a wildcard there.

A pattern that matches **nothing** raises an inventory error — we'd rather fail loud than silently include zero classes. If that's not what you want, `--ignore-class-not-found` drops the unmatched pattern instead, mirroring how missing exact names already behave.

## How it works under the hood

No backend was modified to make this happen. When Kapitan sees a wildcard `classes:` entry anywhere under `inventory/targets/` or `inventory/classes/`, it materializes a **temporary copy** of the inventory tree with those entries pre-expanded, then points the chosen backend — reclass, reclass-rs, or omegaconf — at the copy. The backend never learns wildcards exist. The temp tree is cleaned up on exit, and relative symlinks that pointed outside the original tree get rewritten to absolute paths so they still resolve in the copy.

The cost when you're not using wildcards is effectively nothing: a cheap text scan skips any file with no glob metacharacter in it, which is almost every file in a normal inventory. So leaving the flag off — the default — buys you nothing to worry about.

That's the whole feature. List shrinks, new classes get picked up automatically, and the backend stays none the wiser.
