---
title: "Kapitan Troubleshooting: Fix Common Errors & Issues"
description: "Common Kapitan errors and how to resolve them. Covers inventory, compilation, input types, references, and installation issues."
---

# :kapitan-logo: **Troubleshooting**

This page lists common errors and their resolutions. If your error is not here, try the [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3) Slack channel or [GitHub Discussions](https://github.com/kapicorp/kapitan/discussions).

## Installation and environment

### Python version errors

**Symptom:** `kapitan` fails to install or run with syntax or import errors.

Kapitan requires **Python 3.10 or newer**. Check your version:

```shell
python3 --version
```

If you are using an older Python, upgrade or use the Docker image instead.

### Docker permission issues

**Symptom:** Files created by the Docker container are owned by root.

On Linux, add `-u $(id -u)` to your `docker run` command:

```shell
docker run -t --rm -u $(id -u) -v $(pwd):/src:delegated kapicorp/kapitan compile
```

## Inventory errors

### `No inventory targets discovered at path: ...`

**Cause:** The inventory path does not exist or does not contain any targets.

**Resolution:**

- Ensure you are running `kapitan compile` from the repository root.
- Verify that `inventory/targets/` exists and contains at least one `.yml` or `.yaml` file.
- If your inventory is in a non-default location, pass `--inventory-path`:

```shell
kapitan compile --inventory-path ./my-inventory
```

### `Error: no targets found`

**Cause:** You used `-t` or `--target` with a name that does not exist.

**Resolution:**

- List available targets with:

```shell
kapitan inventory --list-targets
```

- Target names reflect the directory structure under `inventory/targets/`. A file at `inventory/targets/teams/devops/grafana.yml` becomes `teams.devops.grafana`.

### `InventoryError: <target_name>: parameters is empty`

**Cause:** The target file exists but has no `parameters` section.

**Resolution:** Add a `parameters` block to the target, even if minimal:

```yaml
parameters:
  kapitan:
    vars:
      target: my-target
```

### `InventoryError: <target_name>: parameters.kapitan has no assignment`

**Cause:** The target is missing the `parameters.kapitan` structure that defines compile inputs.

**Resolution:** Ensure the target has a `kapitan` section with at least an empty `compile` list if there are no inputs:

```yaml
parameters:
  kapitan:
    compile: []
```

### `Class <class_name> not found`

**Cause:** A target or class references a class that does not exist in the inventory.

**Resolution:**

- Verify the class file exists under `inventory/classes/`.
- Check that the class name matches the relative path. For example, `inventory/classes/common.yml` is `common`, and `inventory/classes/teams/app.yml` is `teams.app`.
- Ensure there are no typos in the `classes:` list.
- If you use `--enable-class-wildcards`, verify that the pattern actually matches existing files.

## Compilation errors

### `CompileError: Error compiling targets: ...`

**Cause:** A compilation step failed. The underlying error is usually printed above this line.

**Resolution:**

- Run with `--verbose` to see the full traceback.
- Check that all `input_paths` exist and point to the correct files.
- Verify that template syntax is valid for the input type you are using.

### `InventoryError` during compilation

**Cause:** The inventory backend encountered an error while rendering.

**Resolution:**

- If you are using **reclass**, check for circular class references and invalid `${...}` interpolation syntax.
- If you are using **omegaconf**, verify that all YAML files are well-formed and that custom resolvers are registered correctly.
- If you are using **reclass-rs**, ensure the Rust binary is installed and compatible with your inventory.

## Input type errors

### Helm: `helm template` fails or chart not found

**Cause:** The Helm input type cannot locate the chart or Helm values are invalid.

**Resolution:**

- Verify that `input_paths` points to a valid Helm chart directory.
- If you fetch charts with the dependency manager, run `kapitan compile --fetch` first.
- Ensure `helm_values` matches the chart's values schema.

### Kustomize: `input_paths` not found

**Cause:** The Kustomize overlay or base directory is missing.

**Resolution:**

- Verify the path exists relative to the repository root.
- Ensure the directory contains a `kustomization.yaml`.

### Jsonnet: `RUNTIME ERROR` or `failed to compile`

**Cause:** The Jsonnet file has a syntax error, a missing import, or an assertion failure.

**Resolution:**

- Run with `--verbose` to see the exact line number.
- Verify that `lib/kapitan.libjsonnet` is available if you import it.
- Check assertion messages for hints about which inventory value is invalid.

## References and secrets

### `?{gpg:...}` or `?{vault:...}` not revealed

**Cause:** The reference exists in the inventory but the secret file is missing from the `refs/` directory.

**Resolution:**

- Ensure the secret was created with `kapitan refs --write ...`.
- Verify that the `refs/` path is correct.
- For GPG, ensure your key is in the keychain and the `GPG_HOME` environment is set if needed.

### `RefError` or `KeyError` for references

**Cause:** A reference tag is malformed or the backend is not configured.

**Resolution:**

- Check the reference syntax: `?{backend:path}`.
- Supported backends: `gpg`, `vault`, `awskms`, `gkms`, `azkv`.
- Ensure the corresponding backend dependencies and credentials are available.

## Performance

### Compilation is slow

**Cause:** Large inventories, many targets, or slow input types.

**Resolution:**

- Compile only the target you need: `kapitan compile -t <target>`.
- Increase parallelism with `-p` (defaults to available CPU count).
- Consider switching to the **reclass-rs** backend for faster inventory rendering.
- If using OmegaConf, check for expensive custom resolvers.

## Next steps

If these resolutions do not solve your problem:

- [Read the core concepts](core_concepts.md) to verify your inventory structure.
- [Browse the FAQ](../FAQ.md) for additional questions.
- [Join `#kapitan` on Slack](https://kubernetes.slack.com/archives/C981W2HD3) and search prior discussions.
- [Open a GitHub Discussion](https://github.com/kapicorp/kapitan/discussions) with the error output and your inventory layout.
