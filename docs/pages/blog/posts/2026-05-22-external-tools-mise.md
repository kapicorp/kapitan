---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 3m
date: 2026-05-22
title: "Managing Kapitan's External Tools with mise"
description: "How we moved Kapitan to mise to pin helm, kustomize, cue and uv versions for reproducible dev and CI setups."
---

# Managing Kapitan's External Tools with mise

Kapitan is not pure Python. The test suite needs `helm`, `kustomize` and
`cue` on the PATH. Contributors installed them however they liked, so the
versions on a laptop and in CI could differ, and a test could pass in one
place and fail in the other.

The repository now uses [`mise`](https://mise.jdx.dev/) to install and pin
those tools. `uv` still manages Python dependencies; `mise` manages the
binaries, including `uv` itself. This is a contributor-facing change: it
does not affect what `kapitan compile` produces.

<!-- more -->

## mise.toml and mise.lock

The pins live in `mise.toml` at the repository root:

```toml
[tools]
# Keep Helm on v3 until Helm v4 behavior is explicitly validated in tests/CI.
helm = "3.19.5"
kustomize = "5.8.1"
cue = "0.15.4"
uv = "0.9.18"
go = "1.26.4"
```

`uv` is in the list so there is one bootstrap path instead of two: `mise`
installs `uv`, and the Makefile runs `uv` through `mise exec`. `go` was added
later so `uv` can build Python packages that need a Go compiler.

Helm is held at v3 on purpose, as the comment says, until Helm v4 has been
validated against the tests and CI.

Next to it, `mise.lock` records download URLs and checksums per tool for
linux and macOS on x64 and arm64, and for Windows on x64. With
`mise install --locked`, every machine gets the same checksum-verified
binaries.

## Setting up as a contributor

Install `mise` itself first, following the
[getting started guide](https://mise.jdx.dev/getting-started.html). The rest
is the same command as before:

```bash
make setup
```

It installs the pinned toolchain through `mise`, then the Python
dependencies with `uv sync --locked`, then the pre-commit hooks. The
toolchain step is also available on its own:

```console
$ make install_tools
===== Installing Development Toolchain via mise =====
uv 0.9.18
v3.19.5+g4a19a5b
v5.8.1
cue version v0.15.4
go version go1.26.4 linux/amd64
```

`make install_tools` runs `mise install --locked` and prints each tool's
version. It replaces `make install_external_tools`, which used a separate
`curl | bash` installer per tool, and `make install_uv`. Both targets are
gone.

## Running commands through mise

Makefile targets such as `make test`, `make lint` and `make format` already
run through `mise`. When calling tools directly, prefix them with
`mise exec --`:

```bash
mise exec -- uv run kapitan <command>
mise exec -- uv run pytest --no-cov tests/test_vault_transit.py
```

An alias saves typing:

```bash
alias kapitan='mise exec -- uv run kapitan'
```

## CI

CI used to install the tools itself: `curl` for Helm, an install script for
Kustomize, a GitHub API lookup for the latest CUE release, and a cache step
on top. Besides the amount of YAML, "latest CUE" meant CI could change
without a commit.

The workflows now use [`jdx/mise-action`](https://github.com/jdx/mise-action)
with `MISE_LOCKED=1`, which installs the same locked versions as
`make install_tools` does locally. A test that passes locally runs against
the same tool versions in CI.
