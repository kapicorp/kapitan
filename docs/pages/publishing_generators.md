---
title: "Publishing Kapitan Generators as OCI Artifacts"
description: "Learn how to package and publish Kapitan generators as OCI artifacts with kapitan publish or oras for teams to consume."
---

# :kapitan-logo: Publishing generators as OCI artifacts

Kapitan's [OCI dependency type](external_dependencies.md#defining-dependencies) lets you pull generator
bundles from any OCI-compliant registry. This page walks through the other half of that workflow:
how to package your own generators and publish them so teams or projects can consume them by
reference.

`kapitan publish` packs and pushes a directory in one step. The [**oras**](https://oras.land/) CLI
is the alternative when you need a different artifact layout, such as several layers.

---

## What is a generator bundle?

A generator bundle is an ordinary directory that **Kapitan** will copy into a target's input path
before compilation. For a **Kadet** generator it typically looks like this:

```
my-generator/
├── __init__.py        # entry point must define main()
└── lib/               # any helper modules
    └── utils.py
```

The contents are entirely up to you. Kapitan will copy the directory (or the declared `subpath`
within it) verbatim, so the bundle can also contain **Jinja2** templates, static YAML, or any other
input type.

---

## Prerequisites

`kapitan publish` needs the optional `oras` Python package (`pip install kapitan[oci]`). To push
with the `oras` CLI instead, install it by following the [official installation guide](https://oras.land/docs/installation).

You also need write access to an OCI registry (GHCR, Docker Hub, a private Harbor instance, etc.)
and your credentials available via `docker login` or environment variables.

---

## Pushing with `kapitan publish`

```shell
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin
kapitan publish my-generator ghcr.io/<org>/<generator>:1.2.0
```

The command prints the manifest digest, for example
`sha256:3ef9422c7178827c3c22129344cbaed868c00c8bbf120f22a51806afb9491eac`. Consumers pin it in
`source` as described under [Tagging strategy](#tagging-strategy). Pushing to an existing tag moves the tag.

The regular files of the directory become one uncompressed tar layer
(`application/vnd.oci.image.layer.v1.tar`) whose root is the directory itself, so consumers need no
`subpath`. Entries are sorted and carry mtime 0, owner 0 and mode 0644, or 0755 for files the owner
can execute. The same tree therefore gives the same digest on every machine and every run. The
manifest uses the OCI empty config and the artifact type `application/vnd.kapitan.generator.v1`.

Files and directories whose name starts with a dot, such as `.git`, are not packed.
`kapitan compile --fetch` skips them when it copies a dependency, so they would not reach
consumers. A symlink or other special file fails the command, so nothing outside the directory is
pushed.

Credentials come from the same places as for fetching: `OCI_USERNAME` and `OCI_PASSWORD`, or what
`docker login` or `oras login` stored. See the `oci` tab under
[External dependencies](external_dependencies.md#defining-dependencies). Add `--insecure` for a
registry that only serves plain HTTP.

---

## Pushing with oras

Authenticate with your registry, then push the directory in a single command:

```shell
# Authenticate (GHCR example)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin

# Push version 1.2.0 — run from INSIDE the generator directory
cd my-generator
oras push ghcr.io/kapicorp/generators:1.2.0 \
  --config /dev/null:application/vnd.oci.image.config.v1+json \
  .
```

oras automatically compresses the directory to `.tar.gz` before upload.

!!! warning "Run `oras push` from inside the generator directory"
    oras preserves the exact path you specify at push time. If you push
    `system/generators/mygenerator/` from a parent directory, oras recreates that
    full path on pull — your files land at
    `output_path/system/generators/mygenerator/` instead of `output_path/`.

    **Always `cd` into the directory you want to publish and push `.`**, or
    specify `subpath: <the-pushed-path>` in the consumer inventory to tell
    Kapitan which subdirectory to extract.

    Kapitan logs the artifact root contents at `INFO` level on every pull so
    you can immediately see what paths are inside the image.

!!! warning "Registry compatibility: always supply `--config`"
    Without `--config`, oras defaults to the deprecated
    `application/vnd.oci.artifact.manifest.v1+json` format. Several registries — including
    **GitLab Container Registry** — reject that format.
    Passing `--config /dev/null:application/vnd.oci.image.config.v1+json` instructs oras to
    use the standard OCI *image* manifest, which is accepted by all compliant registries.

!!! tip "Filtering by media type"
    If you publish multiple different artifact types under the same image (e.g. a generator bundle
    alongside a schema file) you can annotate each layer with a custom media type:

    ```shell
    cd my-generator
    oras push ghcr.io/kapicorp/generators:1.2.0 \
      --config /dev/null:application/vnd.oci.image.config.v1+json \
      .:application/vnd.oci.image.layer.v1.tar+gzip
    ```

    Consumers can then set `media_type: application/vnd.oci.image.layer.v1.tar+gzip` in
    their inventory to pull only that layer. For single-artifact images this is unnecessary.

After a successful push, record the immutable digest shown in the output for reproducible deployments:

```
Pushed [registry] ghcr.io/kapicorp/generators:1.2.0
Digest: sha256:abc123...
```

---

## Tagging strategy

| Scenario | Recommended `source` value |
|---|---|
| Latest of a moving branch | `ghcr.io/org/generators:latest` |
| Pinned release | `ghcr.io/org/generators:1.2.0` |
| Fully reproducible (immutable) | `ghcr.io/org/generators@sha256:<digest>` |

Production Kapitan inventories should always use a pinned tag or digest. Use `latest` only during
active development.

---

## Consuming the published artifact

Once pushed, reference the image in any target's inventory:

```yaml
parameters:
  kapitan:
    dependencies:
    - type: oci
      source: ghcr.io/kapicorp/generators:1.2.0
      output_path: components/generators
      # No subpath needed when the artifact was pushed from inside the directory
    compile:
    - input_type: kadet
      input_paths:
      - components/generators
      output_path: .
```

If you pushed from a parent directory (e.g. `oras push ... my-generator/`), add
`subpath: my-generator` to tell Kapitan which subdirectory to extract:

```yaml
    - type: oci
      source: ghcr.io/kapicorp/generators:1.2.0
      output_path: components/generators
      subpath: my-generator
```

Then compile with `--fetch`:

```shell
kapitan compile --fetch
```

`--fetch` only pulls if the artifact is not already cached locally — subsequent runs are instant.
Use `--force-fetch` to invalidate the cache and re-pull regardless.

See [External dependencies OCI](external_dependencies.md#defining-dependencies) for the full
reference of available fields.
