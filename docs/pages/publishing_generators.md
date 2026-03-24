# :kapitan-logo: Publishing generators as OCI artifacts

Kapitan's [OCI dependency type](external_dependencies.md#defining-dependencies) lets you pull generator
bundles from any OCI-compliant registry. This page walks through the other half of that workflow:
how to package your own generators and publish them so teams or projects can consume them by
reference.

Publishing uses the [**oras**](https://oras.land/) CLI, a small, standalone binary purpose-built
for pushing and pulling arbitrary files to OCI registries.

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

Install the `oras` CLI by following the [official installation guide](https://oras.land/docs/installation).

You also need write access to an OCI registry (GHCR, Docker Hub, a private Harbor instance, etc.)
and your credentials available via `docker login` or environment variables.

---

## Pushing a generator

Authenticate with your registry, then push the directory in a single command:

```shell
# Authenticate (GHCR example)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin

# Push version 1.2.0
oras push ghcr.io/kapicorp/generators:1.2.0 my-generator/
```

oras automatically compresses the directory to `.tar.gz` before upload.

!!! tip "Filtering by media type"
    If you publish multiple different artifact types under the same image (e.g. a generator bundle
    alongside a schema file) you can annotate each layer with a custom media type:

    ```shell
    oras push ghcr.io/kapicorp/generators:1.2.0 \
      my-generator/:application/vnd.kapitan.generator.layer.v1.tar+gzip
    ```

    Consumers can then set `media_type: application/vnd.kapitan.generator.layer.v1.tar+gzip` in
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
      subpath: my-generator        # optional: copy only this sub-directory
    compile:
    - input_type: kadet
      input_paths:
      - components/generators
      output_path: .
```

See [External dependencies OCI](external_dependencies.md#defining-dependencies) for the full
reference of available fields.
