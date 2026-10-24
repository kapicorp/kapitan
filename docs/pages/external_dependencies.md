---
title: "Kapitan External Dependencies: Git, HTTP, Helm, OCI"
description: "Learn how to fetch external dependencies in Kapitan from Git, HTTP, Helm, and OCI remote sources."
---

# :kapitan-logo: External dependencies

**Kapitan** has the functionality to fetch external dependencies from remote locations.

Supported dependencies types are:

- [git](#defining-dependencies)
- [http](#defining-dependencies)
- [helm](#defining-dependencies)
- [oci](#defining-dependencies)


## Usage

*Kapitan* by default will not attempt to download any dependency, and rely on what is already available.

### Basic fetching

You can use the `fetch` option to explicitly fetch the dependencies:

=== "cli"

    ```shell
    kapitan compile --fetch
    ```

=== "dotfile"

    !!! code "`.kapitan`"
        to make it default, then simply use `kapitan compile`

        ```yaml
        ...
        compile:
          fetch: true
        ```


This will download the dependencies and store them at their respective `output_path`.

### Overwrite local changes

When fetching a dependency, **Kapitan** will refuse to overwrite existing files to preserve your local modifications.

Use the `force-fetch` option to force overwrite your local files in the `output_path`.


=== "cli"

    ```shell
    kapitan compile --force-fetch
    ```

=== "dotfile"

    !!! code "`.kapitan`"
        to make it default, then simply use `kapitan compile`

        ```yaml
        ...
        compile:
          force-fetch: true
        ```

### Fetching classes

A dependency can fetch inventory classes. With `--fetch`, Kapitan loads the inventory without the classes that are still missing, fetches the dependencies, and reloads the inventory, so a fetched class takes effect in the same run:

```yaml
# inventory/targets/cert-manager.yml
classes:
  - recipes.cert-manager # fetched below
parameters:
  kapitan:
    dependencies:
      - type: git
        source: https://github.com/example/recipes.git
        ref: v1.0.0
        subdir: cert-manager
        output_path: inventory/classes/recipes/cert-manager
```

A fetched class can declare dependencies of its own, including further classes. Kapitan repeats fetch and reload until a round adds no new or changed dependency. After 5 rounds that still add dependencies, the compile fails and names the classes still missing.

Until the last reload, references that point into a class that isn't fetched yet are skipped, and only the last load reports errors. A dependency entry can't use values that only the class it fetches provides. With the `reclass-rs` backend, a load that reclass-rs can't render because of such references is rendered with `reclass`.

`--fetch` keeps existing files, so after raising the pin of a fetched class use `--force-fetch`, or `force_fetch: true` on the entry. Plain `kapitan compile` also reloads after fetching `force_fetch: true` entries, but it loads the inventory before fetching, so a class that isn't there yet needs `--fetch`.

With `--labels`, targets are matched on the labels known in each round. A target whose labels come only from a class it fetches isn't matched before that class is there.

Fetched classes usually come from someone else, so Kapitan limits what they can do:

- A dependency declared in a fetched class must write below that class's own `output_path`. A fetched class is a class file at or below the `output_path` of a dependency inside `inventory/classes`. Its `parameters.kapitan.dependencies` list and each `output_path` in it must be literal values, because interpolations can't be checked before the class is loaded.
- Two dependencies that fetch different sources into the same `output_path` fail, and the error names both.

### Caching

Kapitan also supports caching Use the `--cache` flag to cache the fetched items in the `.dependency_cache` directory in the root project directory.

    ```shell
    kapitan compile --cache --fetch
    ```

### Defining dependencies

=== "git"

    **Syntax**

    ```yaml
    parameters:
      kapitan:
        dependencies:
        - type: git
          output_path: path/to/dir
          source: git_url # mkdocs (1)!
          subdir: relative/path/from/repo/root (optional) # mkdocs (2)!
          ref: branch, tag, or commit SHA (optional, default: remote HEAD) # mkdocs (3)!
          submodules: true/false (optional) # mkdocs (4)!
    ```

    1. Git types can fetch external `git` repositories through either HTTP/HTTPS or SSH URLs.
    2. Optional supports for cloning just a sub-directory
    3. `ref` accepts any git-resolvable value: a branch name (e.g. `main`), a tag (e.g. `v1.2.0`), or a full/short commit SHA. When omitted, the remote's default branch is used (`origin/HEAD`).
    4. Optional support to disable fetching the submodules of a repo.

    !!! note

        This type depends on the `git` binary installed on your system and available to **Kapitan**.

    **Example**

    Say we want to fetch the source code from our kapitan repository, specifically, `kapicorp/kapitan/kapitan/version.py`. Let's create a very simple target file `inventory/targets/kapitan-example.yml`.

    ```yaml
    parameters:
      kapitan:
        vars:
          target: kapitan-example
        dependencies:
        - type: git
          output_path: source/kapitan
          source: git@github.com:kapicorp/kapitan.git
          subdir: kapitan
          ref: master
          submodules: true
        compile:
        - input_paths:
          - source/kapitan/version.py
          input_type: jinja2 # just to copy the file over to target
          output_path: .
    ```

=== "http"

    **Syntax**

    ```yaml
    parameters:
      kapitan:
        dependencies:
        - type: http | https # mkdocs (2)!
          output_path: path/to/file # mkdocs (1)!
          source: http[s]://<url> # mkdocs (2)!
          unpack: True | False # mkdocs (3)!
    ```

    1. `output_path` must fully specify the file name. For example:
    2. http[s] types can fetch external dependencies available at `http://` or `https://` URL.
    3. archive mode: download and unpack

    **Example**

    === "Single file"


    === "Archive"

    Say we want to download kapitan README.md file. Since it's on Github, we can access it as <https://raw.githubusercontent.com/kapicorp/kapitan/master/README.md>. Using the following inventory, we can copy this to our target folder:

    ```yaml
    parameters:
      kapitan:
        vars:
          target: kapitan-example
        dependencies:
        - type: https
          output_path: README.md
          source: https://raw.githubusercontent.com/kapicorp/kapitan/master/README.md
        compile:
        - input_paths:
          - README.md
          input_type: jinja2
          output_path: .
    ```

=== "helm"

    **Syntax**

    ```yaml
    parameters:
      kapitan:
        dependencies:
        - type: helm
          output_path: path/to/chart
          source: http[s]|oci://<helm_chart_repository_url>
          version: <specific chart version>
          chart_name: <name of chart>
          helm_path: <helm binary>
    ```

    Fetches helm charts and any specific subcharts in the `requirements.yaml` file.

    `helm_path` can be used to specify where the `helm` binary name or path.
    It defaults to the value of the `KAPITAN_HELM_PATH` environment var or simply to `helm` if neither is set.
    You should specify only if you don't want the default behavior.

    `source` can be either the URL to a chart repository, or the URL to a chart on an OCI registry (supported since Helm 3.8.0).

    **Example**

    If we want to download the prometheus helm chart we simply add the dependency to the monitoring target.
    We want a specific version `11.3.0` so we put that in.

    ```yaml
    parameters:
      kapitan:
        vars:
          target: monitoring
        dependencies:
          - type: helm
            output_path: charts/prometheus
            source: https://kubernetes-charts.storage.googleapis.com
            version: 11.3.0
            chart_name: prometheus
        compile:
          - input_type: helm
            output_path: .
            input_paths:
              - charts/prometheus
            helm_values:
            alertmanager:
                enabled: false
            helm_params:
              namespace: monitoring
              name: prometheus
    ```

=== "oci"

    **Syntax**

    ```yaml
    parameters:
      kapitan:
        dependencies:
        - type: oci
          output_path: path/to/dir # mkdocs (1)!
          source: <registry>/<repository>:<tag> # mkdocs (2)!
          subpath: relative/path/inside/artifact # mkdocs (3)!
          insecure: false # mkdocs (4)!
          tls_verify: true # mkdocs (5)!
    ```

    1. Directory where the pulled artifact contents will be written.
    2. OCI reference in the form `registry/repo:tag` or `registry/repo@sha256:<digest>` for pinned pulls.
    3. Optional sub-directory inside the pulled artifact to copy instead of the entire artifact root. Required when the artifact was pushed from a parent directory (oras preserves push-time paths).
    4. Set to `true` to allow pulling from an HTTP (non-TLS) registry. Defaults to `false`. Note: this is distinct from TLS certificate verification use `tls_verify` for self-signed certificates.
    5. Controls TLS certificate verification. Set to `false` to skip verification (e.g. self-signed certs in dev), or provide a path to a custom CA bundle as a string (e.g. `"/etc/ssl/certs/my-ca.crt"`). Defaults to `true`.

    !!! note

        This dependency type requires the optional `oras` Python package. Install it with:
        ```shell
        pip install kapitan[oci]
        ```

        For a full guide on packaging and publishing your own generator bundles, see
        [Publishing generators as OCI artifacts](publishing_generators.md).

    **Authentication**

    Credentials are never stored in the inventory. Kapitan supports two authentication approaches:

    **Docker credential store (recommended)** run `docker login` or `oras login` before compiling.
    Kapitan will pick up the stored credentials automatically:

    ```shell
    # GitHub Container Registry
    echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

    # Generic registry
    oras login registry.example.com -u <username> -p <password>
    ```

    **Environment variables** set `OCI_USERNAME` and `OCI_PASSWORD` in the environment.
    Kapitan will call `login` on the registry automatically before pulling:

    ```shell
    export OCI_USERNAME=myuser
    export OCI_PASSWORD=$GITHUB_TOKEN
    kapitan compile
    ```

    This is the preferred approach for CI/CD pipelines where credentials are injected as secrets.

    **Example**

    Fetching a Kapitan generator bundle published to GHCR and making it available as a Kadet component:

    ```yaml
    parameters:
      kapitan:
        vars:
          target: my-service
        dependencies:
        - type: oci
          source: ghcr.io/kapicorp/generators:1.2.0
          output_path: components/generators
          subpath: generators/kubectl
        compile:
        - input_type: kadet
          input_paths:
          - components/generators
          output_path: .
    ```

    You can also pin to an immutable digest to guarantee reproducible builds:

    ```yaml
    - type: oci
      source: ghcr.io/kapicorp/generators@sha256:abc123...
      output_path: components/generators
    ```
