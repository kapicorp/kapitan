---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 5m
date: 2026-06-17
title: "Sharing Kapitan Generators as OCI Artifacts"
description: "Package reusable Kapitan generators, push them to an OCI registry with oras, and pull them as a dependency on compile."
---

# Sharing Kapitan Generators as OCI Artifacts

A Kadet component that wraps a Deployment the way a platform team wants it, or
a Jinja2 template for an in-house CRD, tends to get copied from repo to repo.
The copies drift, and after a few months nobody knows which one is current.
Git submodules address that, at the cost of their own workflow.

Since v0.36.0, Kapitan can pull generators from an OCI registry: the same
GHCR, Harbor or plain Docker registry that holds your container images. You
publish a versioned bundle with `oras`, reference it in the inventory, and
`kapitan compile --fetch` pulls it.

<!-- more -->

## What a bundle is

There is no special format. A bundle is a directory that Kapitan copies into
the dependency's `output_path` before compiling. A Kadet generator usually
looks like this:

```
my-generator/
├── __init__.py        # entry point, defines main()
└── lib/
    └── utils.py
```

It can equally hold Jinja2 templates, static YAML, or anything else your
`compile` entries consume. Kapitan copies the directory, or a `subpath`
inside it, verbatim.

## Publishing with oras

Publishing is done with the [`oras`](https://oras.land/) CLI, not with
Kapitan. Install it from the
[official guide](https://oras.land/docs/installation), log in, and push from
inside the generator directory:

```shell
# Authenticate (GHCR example)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin

# Push version 1.2.0 from inside the generator directory
cd my-generator
oras push ghcr.io/<org>/<generator>:1.2.0 \
  --config /dev/null:application/vnd.oci.image.config.v1+json \
  .
```

oras packs the directory as `.tar.gz` and prints the digest after the push.
Keep it if you want to pin by digest later:

```
Pushed [registry] ghcr.io/<org>/<generator>:1.2.0
Digest: sha256:abc123...
```

oras keeps the path you pass at push time. Push `my-generator/` from its
parent directory and the files arrive at `output_path/my-generator/` instead
of `output_path/`. Either push `.` from inside the directory, or set
`subpath:` in the consuming inventory to the path you pushed.

The `--config` flag makes oras write an image-spec v1.0 manifest with a
standard image config. Without it, oras writes an image-spec v1.1 manifest
with an `artifactType` and an empty config.

## Consuming it as a dependency

The `oci` dependency type sits next to `git`, `http` and `helm`:

```yaml
parameters:
  kapitan:
    dependencies:
    - type: oci
      source: ghcr.io/<org>/<generator>:1.2.0
      output_path: components/generators
    compile:
    - input_type: kadet
      input_paths:
      - components/generators
      output_path: .
```

`source` is a bare registry reference: `registry/repo:tag`, or
`registry/repo@sha256:<digest>` for an immutable pull. A scheme such as
`oci://`, `https://` or `http://` fails validation with a message telling you
to drop it.

```shell
kapitan compile --fetch
```

`--fetch` pulls the artifact on every run, but it does not overwrite files
that already exist in `output_path`. After bumping the tag, run with
`--force-fetch` so the new version replaces the old files.

If the files end up one level too deep and `input_paths` points at an empty
directory, check the log. On every pull Kapitan logs the artifact's top-level
entries at `INFO`, as `artifact root contains: [...]`, which tells you what
to set `subpath` to.

## Pinning

Tags can be moved. `:latest` next week is not `:latest` today, and a
generator that changes without a change in your repo is hard to debug. Pin a
release tag, or a digest:

```yaml
- type: oci
  source: ghcr.io/<org>/<generator>@sha256:abc123...
  output_path: components/generators
```

A digest always resolves to the same content. Leave `:latest` for local
development.

## Registries without proper TLS

Two fields cover registries that are not fully set up. `insecure: true` is
for a registry that speaks plain HTTP, such as a dev box or an internal
mirror. `tls_verify` is for a registry that has TLS with a certificate you do
not trust by default: `false` skips verification, and a string is used as
the path to a CA bundle, so verification still happens against your own CA:

```yaml
- type: oci
  source: registry.internal:5000/generators:1.2.0
  output_path: components/generators
  tls_verify: "/etc/ssl/certs/internal-ca.crt"
```

## Credentials

Registry credentials do not belong in the inventory, and Kapitan does not
read them from there. It uses the Docker credential store, so a
`docker login` or `oras login` before compiling is enough. In CI, where
secrets usually arrive as environment variables, set `OCI_USERNAME` and
`OCI_PASSWORD`; when both are set Kapitan authenticates with them before
pulling:

```shell
export OCI_USERNAME=myuser
export OCI_PASSWORD=$GITHUB_TOKEN
kapitan compile --fetch
```

The `oci` type needs the `oras` Python package, which is an optional extra.
Without it, an OCI dependency raises an `ImportError` that names the fix:

```shell
pip install kapitan[oci]
```

## Further reading

The field reference is in
[External dependencies](../../external_dependencies.md), and the publishing
side is covered in more depth in
[Publishing generators as OCI artifacts](../../publishing_generators.md).
