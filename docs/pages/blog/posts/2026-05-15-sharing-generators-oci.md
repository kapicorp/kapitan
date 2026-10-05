---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 6m
date: 2026-05-15
title: "Sharing Kapitan Generators as OCI Artifacts"
description: "Package reusable Kapitan generators, push them to an OCI registry with oras, and pull them as a dependency on compile."
---

# :kapitan-logo: **Sharing Kapitan Generators as OCI Artifacts**

We keep writing the same generators twice. A Kadet component that wraps a Deployment the way our platform team likes it, a Jinja2 template for some bespoke CRD — and then the next repo needs it, so it gets copy-pasted, drifts, and three months later nobody remembers which version is the good one. Git submodules sort of solve this, but they are their own kind of misery.

So we taught Kapitan to pull generators straight from an OCI registry. The same place your container images live — GHCR, Harbor, a plain Docker registry — can now hand out versioned, digest-pinnable generator bundles. You publish once with `oras`, reference the image in your inventory, and `kapitan compile --fetch` does the rest.

<!-- more -->

## What a bundle actually is

There is no special format here. A generator bundle is just a directory that Kapitan copies into your target's input path before compilation. For a Kadet generator it usually looks like this:

```
my-generator/
├── __init__.py        # entry point must define main()
└── lib/
    └── utils.py
```

The contents are up to you. It can be Kadet, Jinja2 templates, static YAML, whatever your `compile` block knows how to consume. Kapitan copies the directory (or a declared `subpath` inside it) verbatim.

## Publishing with oras

Publishing happens with the [`oras`](https://oras.land/) CLI, not Kapitan. It is a small standalone binary for pushing arbitrary files to OCI registries. Install it from the [official guide](https://oras.land/docs/installation), then log in to your registry and push:

```shell
# Authenticate (GHCR example)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin

# Push version 1.2.0 — run from INSIDE the generator directory
cd my-generator
oras push ghcr.io/kapicorp/generators:1.2.0 \
  --config /dev/null:application/vnd.oci.image.config.v1+json \
  .
```

oras compresses the directory to `.tar.gz` for you. After the push it prints a digest — write that down if you want reproducible deploys:

```
Pushed [registry] ghcr.io/kapicorp/generators:1.2.0
Digest: sha256:abc123...
```

Two things bite people here, so we will be blunt about them.

!!! warning "Push from inside the directory"
    oras preserves whatever path you hand it at push time. Push `my-generator/` from a parent directory and oras recreates that path on pull, so your files land at `output_path/my-generator/` instead of `output_path/`. Either `cd` into the directory and push `.`, or set `subpath:` in the consumer inventory to match the path you pushed.

!!! warning "Always pass `--config`"
    Without `--config`, oras defaults to the deprecated `application/vnd.oci.artifact.manifest.v1+json` format, and some registries — GitLab Container Registry among them — reject it outright. Passing `--config /dev/null:application/vnd.oci.image.config.v1+json` forces the standard OCI *image* manifest, which every compliant registry accepts.

## Consuming it as a dependency

Now the Kapitan side. The `oci` dependency type lives alongside `git`, `http`, and `helm`. You point it at the image and tell Kapitan where to drop the contents:

```yaml
parameters:
  kapitan:
    dependencies:
    - type: oci
      source: ghcr.io/kapicorp/generators:1.2.0
      output_path: components/generators
    compile:
    - input_type: kadet
      input_paths:
      - components/generators
      output_path: .
```

One detail worth knowing: `source` must be a bare registry reference. If you paste in `oci://ghcr.io/...` out of habit, Kapitan stops you with a validation error telling you to drop the scheme. Same for `https://`. The reference is `registry/repo:tag`, or `registry/repo@sha256:<digest>` when you want an immutable pull.

Then compile with `--fetch`:

```shell
kapitan compile --fetch
```

`--fetch` only pulls when the artifact is not already cached locally, so the second run onwards is instant. Use `--force-fetch` to invalidate the cache and re-pull regardless.

!!! tip "Lost in a nested artifact? Read the log"
    If you forgot to push from inside the directory, the contents end up one level too deep and your `input_paths` point at nothing. Kapitan logs the artifact's top-level entries at `INFO` on every pull — `artifact root contains: [...]` — so you can see exactly what is in there and set `subpath` accordingly instead of guessing.

## Pin it, or regret it later

Tags move. `:latest` today is not `:latest` next week, and a generator that quietly changes underneath you is a debugging session waiting to happen. For anything past active development, pin a real version or a digest:

```yaml
- type: oci
  source: ghcr.io/kapicorp/generators@sha256:abc123...
  output_path: components/generators
```

A digest pulls the same bytes forever. We treat `:latest` as a dev-only convenience and nothing more.

## Registries that aren't perfect

Real registries are messy. Two fields cover the awkward cases.

For a plain-HTTP registry — a dev box, an internal mirror without TLS — set `insecure: true`. For TLS that exists but is self-signed, that is a different problem: use `tls_verify`. Set it to `false` to skip verification entirely, or hand it a path to a CA bundle as a string so verification still happens against your own CA:

```yaml
- type: oci
  source: registry.internal:5000/generators:1.2.0
  output_path: components/generators
  tls_verify: "/etc/ssl/certs/internal-ca.crt"
```

`insecure` and `tls_verify` are genuinely separate switches — one is "no TLS at all", the other is "TLS, but trust this". Mixing them up is the kind of thing that wastes an afternoon.

## Credentials stay out of the inventory

We never put registry credentials in inventory YAML, and Kapitan does not ask you to. It picks them up one of two ways.

The first is the Docker credential store. Run `docker login` (or `oras login`) before compiling and Kapitan reuses the stored token automatically — nothing else to configure. The second, handier for CI where secrets arrive as environment variables, is `OCI_USERNAME` and `OCI_PASSWORD`:

```shell
export OCI_USERNAME=myuser
export OCI_PASSWORD=$GITHUB_TOKEN
kapitan compile --fetch
```

When both are set Kapitan authenticates with them before pulling. In a pipeline that is usually all you need.

!!! note "One optional install"
    The `oci` dependency type needs the `oras` Python package, which Kapitan keeps as an optional extra. If you declare an OCI dependency without it, you get a clear `ImportError` pointing at the fix:

    ```shell
    pip install kapitan[oci]
    ```

## That's the whole loop

Write a generator, `oras push` it to a registry, reference the image as an `oci` dependency, `kapitan compile --fetch`. The bundle is versioned, pinnable to a digest, and shared across every repo that wants it — without a single git submodule.

For the full field reference see [External dependencies](../../external_dependencies.md), and for the publishing side in depth, [Publishing generators as OCI artifacts](../../publishing_generators.md).
