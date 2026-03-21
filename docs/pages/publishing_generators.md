# :kapitan-logo: Publishing generators as OCI artifacts

Kapitan's [OCI dependency type](external_dependencies.md#defining-dependencies) lets you pull generator
bundles from any OCI-compliant registry. This page walks through the other half of that workflow:
how to package your own generators and publish them so teams or projects can consume them by
reference.

The toolchain used here is [**uv**](https://docs.astral.sh/uv/) for running the push script and
[**oras**](https://oras.land/) (Python library) for talking to the registry. No extra binaries are
required.

---

## What is a generator bundle?

A generator bundle is an ordinary directory that **Kapitan** will copy into a target's input path
before compilation. For a **Kadet** generator it typically looks like this:

```
my-generator/
├── __init__.py        # entry point — must define main()
└── lib/               # any helper modules
    └── utils.py
```

The contents are entirely up to you. Kapitan will copy the directory (or the declared `subpath`
within it) verbatim, so the bundle can also contain **Jinja2** templates, static YAML, or any other
input type.

---

## Prerequisites

- **uv** installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Write access to an OCI registry (GHCR, Docker Hub, a private Harbor instance, etc.)
- Your registry credentials available as environment variables or via `docker login`

No other global installs are needed — the push script below declares its own dependencies via
[PEP 723 inline metadata](https://peps.python.org/pep-0723/) and `uv run` handles the rest.

---

## Directory layout

For this example we'll publish a minimal Kadet generator for a Kubernetes `Deployment`:

```
my-generator/
├── __init__.py
└── lib/
    └── workloads.py
push.py                ← the publish script (lives outside the bundle)
```

---

## Writing the push script

Save the following as `push.py` next to your generator directory. Edit the `TARGET` variable for
your registry and repository.

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["oras>=0.2.0"]
# ///
"""
Push a Kapitan generator bundle to an OCI registry.

Usage:
    uv run push.py <tag>

Example:
    uv run push.py 1.2.0
"""

import sys
import os
import oras.client

REGISTRY = "ghcr.io"
REPOSITORY = "kapicorp/generators"
BUNDLE_DIR = "my-generator"              # directory to package and push
MEDIA_TYPE = "application/vnd.kapitan.generator.layer.v1.tar+gzip"  # (1)!


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run push.py <tag>")
        sys.exit(1)

    tag = sys.argv[1]
    target = f"{REGISTRY}/{REPOSITORY}:{tag}"

    client = oras.client.OrasClient(hostname=REGISTRY)
    client.auth.load_configs()           # reads ~/.docker/config.json  (2)!

    print(f"Pushing {BUNDLE_DIR!r} → {target}")
    response = client.push(
        target=target,
        files=[f"{BUNDLE_DIR}:{MEDIA_TYPE}"],  # (3)!
        manifest_annotations={"org.opencontainers.image.title": REPOSITORY},
        disable_path_validation=True,
    )
    print(f"Pushed: {response.status_code}")


if __name__ == "__main__":
    main()
```

1. Setting a custom media type lets consumers filter for this layer specifically via the `media_type`
   field in the Kapitan inventory. You can use any string; this is the convention for Kapitan
   generators.
2. `load_configs()` picks up credentials stored by `docker login` or set via the `ORAS_TOKEN`
   environment variable.
3. The `"path:media_type"` syntax annotates the layer. The directory is automatically compressed to
   a `.tar.gz` blob before upload.

---

## Pushing a new version

```shell
# Authenticate once (GHCR example — substitute your registry)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin

# Push version 1.2.0
uv run push.py 1.2.0
```

After a successful push, record the immutable digest for reproducible deployments:

```shell
# Retrieve the digest (requires the oras CLI or skopeo; shown with skopeo)
skopeo inspect docker://ghcr.io/kapicorp/generators:1.2.0 | python3 -m json.tool | grep Digest
```

!!! note

    If you are iterating locally and don't have `skopeo`, the digest is printed in the ORAS client
    response body. You can also find it on the registry's web UI (GHCR, Docker Hub, Harbor all
    expose it in the image detail page).

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

## GitHub Actions — automated publishing

A minimal workflow that publishes on every version tag:

```yaml
name: Publish generator

on:
  push:
    tags: ["v*"]

jobs:
  push:
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Log in to GHCR
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u "${{ github.actor }}" --password-stdin

      - name: Push generator bundle
        run: uv run push.py "${GITHUB_REF_NAME#v}"   # strips leading 'v' from the tag
```

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

See [External dependencies — OCI](external_dependencies.md#defining-dependencies) for the full
reference of available fields.
