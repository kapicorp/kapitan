---
title: "Kapitan Inventory Backends: reclass vs reclass-rs vs OmegaConf"
description: "Compare Kapitan inventory backends — reclass, reclass-rs, and OmegaConf — and learn which to choose for speed, compatibility, and features."
---

# :kapitan-logo: **Alternative Inventory Backends**

Kapitan's [**inventory**](introduction.md) is pluggable: you can swap the engine
that loads and resolves it without rewriting a single `class`, `target`, or
`parameter`. Three backends ship with Kapitan, and they differ in three things
that matter when you choose one — **speed**, **interpolation syntax**, and **which
features they support**.

* `reclass` (**default**): the original Kapitan inventory (see [reclass](https://github.com/kapicorp/reclass)). Bundled — nothing to install.
* `reclass-rs`: a Rust drop-in replacement, much faster (see [reclass-rs](reclass-rs.md)). Optional extra.
* `omegaconf`: an [OmegaConf](https://github.com/omry/omegaconf)-based alternative with custom resolvers (see [omegaconf](omegaconf.md)). Optional extra, **experimental**.

## Which backend should I use?

- **Stay on `reclass`** unless you have a reason to switch. It is the default, the most mature, and supports every Kapitan inventory feature.
- **Switch to `reclass-rs`** when inventory rendering is slow — large inventories with heavy parameter interpolation in class includes. It is a **drop-in**: same syntax, no inventory changes, just faster ([benchmarks](reclass-rs.md#performance-comparison)). Check the [feature gaps](#feature-support) first.
- **Choose `omegaconf`** only if you specifically want its resolver toolkit (`${merge:}`, `${escape:}`, conditionals, custom Python resolvers). It uses **different interpolation syntax**, so it is **not** a drop-in — existing inventories need [migration](omegaconf.md#migration-from-reclass). It is **experimental**.

## Comparison

| | `reclass` (default) | `reclass-rs` | `omegaconf` |
|---|---|---|---|
| **Install** | bundled | `pip install kapitan[reclass-rs]` | `pip install kapitan[omegaconf]` |
| **Maturity** | stable, default | stable | **experimental** (pre-release dep) |
| **Implementation** | Python | Rust | Python |
| **Speed** | baseline | **much faster** on large inventories ([benchmarks](reclass-rs.md#performance-comparison)) | comparable to reclass |
| **Interpolation syntax** | colon paths `${a:b:c}` | colon paths `${a:b:c}` (same as reclass) | dotted paths `${a.b.c}` + resolvers |
| **Drop-in for reclass?** | — | ✅ yes, same syntax | ❌ no, needs [migration](omegaconf.md#migration-from-reclass) |
| **List merge (class include)** | extend / concatenate | extend / concatenate | extend **+ de-duplicate** (`EXTEND_UNIQUE`) |
| **Custom resolvers** | ❌ | ❌ | ✅ `${merge:}`, `${escape:}`, `${if:}`, user-defined, … |
| **Inventory queries** (`$[...]`, exports) | ✅ | ❌ not supported | ❌ not supported |

!!! warning "List-merge semantics differ"
    `reclass` / `reclass-rs` **concatenate** lists on class inclusion (duplicates
    kept). `omegaconf` de-duplicates (`EXTEND_UNIQUE`) during class merge — but
    its `${merge:...}` resolver keeps duplicates (`EXTEND`). If you switch
    backends, a list that previously had repeated entries may change. Verify
    list-valued parameters after migrating.

## Switching backend

Pick the backend by either:

* (**recommended**) setting it in the [.kapitan config file](../commands/kapitan_dotfile.md):

```yaml
global:
  inventory-backend: reclass-rs
```

* or passing `--inventory-backend=<backend>` on the `kapitan` command line.

## Feature support

`reclass` is the reference: it supports the full feature set.

`reclass-rs` is a drop-in, but a few reclass options are **not implemented yet**
(known gaps, sourced from the [upstream reclass-rs project](https://github.com/projectsyn/reclass-rs)
— may change between versions):

- inventory queries (`$[...]` expressions)
- `allow_none_override: false` (effectively pinned to `true`; Kapitan's default is `true`, so the default case works)
- storage types other than `yaml_fs` (`yaml_git`, `mixed`)

It also has minor behavioral divergences in non-compatible modes (e.g. `null` in
nested references, dots in `compose_node_name`) — see the upstream README. If a
feature you rely on is missing,
[open an issue upstream](https://github.com/projectsyn/reclass-rs/issues).

`omegaconf` supports a different feature set — see
[Differences from Reclass](omegaconf.md#differences-from-reclass) for what is and
isn't supported, plus its resolver catalogue.
