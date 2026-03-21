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

### Caching

Kapitan also supports caching Use the `--cache` flag to cache the fetched items in the `.dependency_cache` directory in the root project directory.

    ```shell
    kapitan compile --cache --fetch
    ```

### Defining dependencies

=== "git"

    ### Syntax

    ```yaml
    parameters:
      kapitan:
        dependencies:
        - type: git
          output_path: path/to/dir
          source: git_url # mkdocs (1)!
          subdir: relative/path/from/repo/root (optional) # mkdocs (2)!
          ref: tag, commit, branch etc. (optional) # mkdocs (3)!
          submodules: true/false (optional) # mkdocs (4)!
    ```

    1. Git types can fetch external `git` repositories through either HTTP/HTTPS or SSH URLs.
    2. Optional supports for cloning just a sub-directory
    3. Optional support for accessing them in specific commits and branches (refs).
    4. Optional support to disable fetching the submodules of a repo.

    !!! note

        This type depends on the `git` binary installed on your system and available to **Kapitan**.

    ### Example

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

    ### Syntax

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

    ### Example

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

    ### Syntax

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

    ### Example

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

    ### Syntax

    ```yaml
    parameters:
      kapitan:
        dependencies:
        - type: oci
          output_path: path/to/dir # mkdocs (1)!
          source: <registry>/<repository>:<tag> # mkdocs (2)!
          subpath: relative/path/inside/artifact # mkdocs (3)!
          media_type: application/vnd.kapitan.generator # mkdocs (4)!
          insecure: false # mkdocs (5)!
    ```

    1. Directory where the pulled artifact contents will be written.
    2. OCI reference in the form `registry/repo:tag` or `registry/repo@sha256:<digest>` for pinned pulls.
    3. Optional sub-directory inside the unpacked artifact to copy instead of the entire artifact root.
    4. Optional media type filter passed to the OCI client when pulling layers.
    5. Set to `true` to allow pulling from an HTTP (non-TLS) registry. Defaults to `false`.

    !!! note

        This dependency type requires the optional `oras` Python package. Install it with:
        ```shell
        pip install kapitan[oci]
        ```

    ### Example

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
