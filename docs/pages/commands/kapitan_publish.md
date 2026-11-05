---
title: "Kapitan publish: Push a Generator to an OCI Registry"
description: "Push a generator directory to an OCI registry with kapitan publish, in the layout the oci dependency type fetches."
---

# :kapitan-logo: **CLI Reference** | `kapitan publish`

## `kapitan publish`

Packs a directory into one tar layer and pushes it to an OCI registry, in the layout the `oci` [external dependency](../external_dependencies.md) type fetches. Prints the manifest digest.

!!! example ""

    ```shell
    kapitan publish components/my-generator ghcr.io/<org>/<generator>:1.2.0
    ```

    ??? example "click to expand output"
        ```shell
        sha256:3ef9422c7178827c3c22129344cbaed868c00c8bbf120f22a51806afb9491eac
        ```

[Publishing generators](../publishing_generators.md#pushing-with-kapitan-publish) describes what is packed, the artifact layout and where credentials come from.

## Flags

The table below is generated from **Kapitan**'s argument parser at docs-build time, so it always matches the installed version. See also the [global flags](kapitan_flags.md) accepted by every command, and the [`.kapitan` dotfile](kapitan_dotfile.md) to set any of these permanently.

<!-- kapitan-flags:command:publish -->
