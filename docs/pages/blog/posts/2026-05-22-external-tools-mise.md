---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 4m
date: 2026-05-22
title: "Managing Kapitan's External Tools with mise"
description: "How we moved Kapitan to mise to pin helm, kustomize, cue and uv versions for reproducible dev and CI setups."
---

# :kapitan-logo: **Managing Kapitan's External Tools with mise**

Kapitan has never been pure Python. To run our test suite you need `helm`, `kustomize` and `cue` on your PATH, and for years we asked contributors to install them however they liked. That worked right up until someone's `kustomize` was a major version ahead of CI's and a test failed for reasons nobody could reproduce.

So we standardised on [`mise`](https://mise.jdx.dev/) to install and pin those tools. `uv` still owns the Python side; `mise` owns everything else. Here's what changed and why it makes your life a little easier.

<!-- more -->

## One file, four pinned tools

The source of truth is a new `mise.toml` at the repo root. It is short on purpose:

```toml
[tools]
# Keep Helm on v3 until Helm v4 behavior is explicitly validated in tests/CI.
helm = "3.19.5"
kustomize = "5.8.1"
cue = "0.15.4"
uv = "0.9.18"
```

Notice `uv` is in there too. We didn't want two different bootstrap stories — one for Python tooling and one for everything else — so `mise` now installs `uv` as well, and the Makefile drives `uv` through `mise exec`.

Alongside it sits a `mise.lock` file with per-platform checksums and download URLs for each tool, covering linux, macOS and Windows on amd64/arm64. That's the bit that makes "works on my machine" mean something: when CI runs `mise install --locked`, it gets the exact same binaries you do, checksum-verified.

!!! note "Why Helm is pinned to v3"
    The comment in `mise.toml` isn't decorative. We're deliberately holding Helm at v3 until Helm v4's behavior is validated against our tests and CI. Pinning makes that decision explicit instead of leaving it to whatever each contributor happened to install.

## Setting up as a contributor

First, install `mise` itself — that's the one thing `mise` can't do for you. Follow the official instructions for your platform and shell at <https://mise.jdx.dev/getting-started.html>.

After that, the full setup is unchanged from before:

```bash
make setup
```

Under the hood this now installs the pinned toolchain via `mise`, then the Python dependencies, then the pre-commit hooks. If you prefer to do it piece by piece, the toolchain step is its own target:

```bash
make install_tools
```

That runs `mise install --locked` and then prints the versions back so you can see what you got:

```console
$ make install_tools
===== Installing Development Toolchain via mise =====
v0.9.18
v3.19.5
{kustomize/v5.8.1  ...}
cue version v0.15.4
```

The old `make install_external_tools` target — the one with the bespoke `curl | bash` installers for each tool — is gone. So is `make install_uv`. Both folded into `make install_tools`.

## Running things through mise

Because `mise` manages the tool versions, you run commands through it rather than relying on whatever's on your PATH. The Makefile already does this for you, but when you invoke Kapitan directly during development:

```bash
mise exec -- uv run kapitan <your command>
```

If that gets tedious, an alias is the obvious fix:

```bash
alias kapitan='mise exec -- uv run kapitan'
```

Same pattern for a one-off test file:

```bash
mise exec -- uv run pytest --no-cov tests/test_vault_transit.py
```

!!! tip "Makefile targets don't need the prefix"
    You only need `mise exec --` when calling tools yourself. `make test`, `make lint`, `make format` and friends already route through `mise` internally, so `make test` just works.

## What changed in CI

CI used to hand-roll tool installation: a `curl` for Helm, a script for Kustomize, a GitHub API lookup to find the latest CUE release, plus a cache step to keep all that from running every build. It worked, but it was a lot of YAML to maintain, and "latest CUE" is exactly the kind of moving target that bites you on a random Tuesday.

Now the workflows use the [`jdx/mise-action`](https://github.com/jdx/mise-action) and the same `mise install --locked` path you run locally. Local and CI bootstrap the toolchain identically, which is the whole point: when a test passes for you, you can trust it'll pass in CI for the same reasons.

We also took the opportunity to delete a stale `default.nix` that nobody used anymore — it still referenced `poetry` and `black` from a setup we'd long since left behind. One less misleading file in the tree.

## The honest summary

This isn't a feature you'll see in your compiled output. It's plumbing. But it's the kind of plumbing that turns "I can't reproduce your CI failure" into "oh, we're on the same `kustomize` now." If you've cloned Kapitan before and wrestled with tool versions, `make setup` should feel a lot less fiddly next time.
