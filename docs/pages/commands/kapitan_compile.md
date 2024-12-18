# :kapitan-logo: **CLI Reference** | `kapitan compile`

## `kapitan compile`

Merges inventory and inputs and produces generated files in the output folder (`/compiled` by default)

## Compile all targets

!!! example ""

    ```shell
    kapitan compile
    ```

    ??? example "click to expand output"
        ```text
        Compiled mysql-generator-fetch (0.18s)
        Compiled vault (0.25s)
        Compiled pritunl (0.22s)
        Compiled gke-pvm-killer (0.05s)
        Compiled examples (0.30s)
        Compiled mysql (0.08s)
        Compiled postgres-proxy (0.06s)
        Compiled echo-server (0.06s)
        Compiled global (0.03s)
        Compiled guestbook-argocd (0.08s)
        Compiled tutorial (0.13s)
        Compiled kapicorp-project-123 (0.03s)
        Compiled kapicorp-demo-march (0.03s)
        Compiled kapicorp-terraform-admin (0.03s)
        Compiled sock-shop (0.32s)
        Compiled tesoro (0.09s)
        Compiled dev-sockshop (0.32s)
        Compiled prod-sockshop (0.38s)
        Compiled argocd (2.29s)
        ```

## Selective compilation

### Using target names

Compiles one or more targets selected by name using `--targets` or `-t`

!!! example ""

    ```shell
    kapitan compile -t mysql tesoro
    ```

    ??? example "click to expand output"
        ```shell
        Compiled mysql (0.06s)
        Compiled tesoro (0.09s)
        ```

### Using labels

Compiles one or more targets selected matching **labels** with  `--labels` or `-l`

!!! info

    This works if you have labelled your targets using the following syntax:

    ```yaml
    parameters:
      ...
      kapitan:
        ...
        labels:
          customer: acme
    ```

    see [**Labels**](../inventory/advanced.md#target-labels) for more details

```shell
$ kapitan compile -l customer=acme
Compiled acme-project (0.14s)
Compiled acme-pipelines (0.10s)
```

## Fetch on compile

Use the `--fetch` flag to fetch [**External Dependencies**](../external_dependencies.md).

```shell
kapitan compile --fetch
```

This will download the dependencies according to their configurations
By default, kapitan does not overwrite an existing item with the same name as that of the fetched inventory items.

Use the `--force-fetch` flag to force fetch (update cache with freshly fetched items) and overwrite inventory items of the same name in the `output_path`.

```shell
kapitan compile --force-fetch
```

Use the `--cache` flag to cache the fetched items in the `.dependency_cache` directory in the root project directory.

```shell
kapitan compile --cache --fetch
```

## Embed references

By default, **Kapitan** references are stored encrypted (for backends that support encription) in the configuration repository under the `/refs` directory.

For instance, a reference tag `?{gpg:targets/minikube-mysql/mysql/password:ec3d54de}` would point to a phisical file on disk under `/refs` like:

!!! example "`refs/targets/minikube-mysql/mysql/password`"

    ```shell
    data: hQEMA8uOJKdm07XTAQgAp5i [[ CUT ]] BwqYc3g7PI09HCJZdU=
    encoding: base64
    recipients:
    - fingerprint: D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C
    type: gpg
    ```

The `--embed-refs` flags tells **Kapitan** to embed these references on compile, alongside the generated output. By doing so, compiled output is self-contained and can be revealed by [**Tesoro**](https://github.com/kapicorp/tesoro) or other tools.

!!! example ""

    ```shell
    kapitan compile --embed-refs
    ```

    See how the compiled output for this specific target changes to embed the actul encrypted content, (marked by `?{gpg: :embedded}` to indicate it is a **gpg** reference) rather than just holding a reference to it (like in this case `?{gpg:targets/minikube-mysql/mysql/password:ec3d54de}` which points to ).

    ??? example "click to expand output"
        ```shell
        diff --git a/examples/kubernetes/compiled/minikube-mysql/manifests/mysql_app.yml b/examples/kubernetes/compiled/minikube-mysql/manifests/mysql_app.yml
        [[ CUT ]]
        apiVersion: v1
        data:
        -  MYSQL_ROOT_PASSWORD: ?{gpg:targets/minikube-mysql/mysql/password:ec3d54de}
        -  MYSQL_ROOT_PASSWORD_SHA256: ?{gpg:targets/minikube-mysql/mysql/password_sha256:122d2732}
        +  MYSQL_ROOT_PASSWORD: ?{gpg:eyJkYXRhIjogImhR [[ CUT ]] gInR5cGUiOiAiZ3BnIn0=:embedded}
        +  MYSQL_ROOT_PASSWORD_SHA256: ?{gpg:eyJkYXRhI [[ CUT ]] eXBlIjogImdwZyJ9:embedded}
        ```

## help

!!! example ""

    ```shell
    kapitan compile --help
    ```

    ??? example "click to expand output"

        ```shell
        usage: kapitan compile [-h] [--inventory-backend {reclass}]
                       [--search-paths JPATH [JPATH ...]]
                       [--jinja2-filters FPATH] [--verbose] [--prune]
                       [--quiet] [--output-path PATH] [--fetch]
                       [--force-fetch] [--force] [--validate]
                       [--parallelism INT] [--indent INT]
                       [--refs-path REFS_PATH] [--reveal] [--embed-refs]
                       [--inventory-path INVENTORY_PATH] [--cache]
                       [--cache-paths PATH [PATH ...]]
                       [--ignore-version-check] [--use-go-jsonnet]
                       [--compose-target-name] [--schemas-path SCHEMAS_PATH]
                       [--yaml-multiline-string-style STYLE]
                       [--yaml-dump-null-as-empty]
                       [--targets TARGET [TARGET ...] | --labels
                       [key=value ...]]

        options:
          -h, --help            show this help message and exit
          --inventory-backend {reclass,reclass-rs}
                                Select the inventory backend to use (default=reclass)
          --search-paths JPATH [JPATH ...], -J JPATH [JPATH ...]
                                set search paths, default is ["."]
          --jinja2-filters FPATH, -J2F FPATH
                                load custom jinja2 filters from any file, default is
                                to put them inside lib/jinja2_filters.py
          --verbose, -v         set verbose mode
          --prune               prune jsonnet output
          --quiet               set quiet mode, only critical output
          --output-path PATH    set output path, default is "."
          --fetch               fetch remote inventories and/or external dependencies
          --force-fetch         overwrite existing inventory and/or dependency item
          --force               overwrite existing inventory and/or dependency item
          --validate            validate compile output against schemas as specified
                                in inventory
          --parallelism INT, -p INT
                                Number of concurrent compile processes, default is 4
          --indent INT, -i INT  Indentation spaces for YAML/JSON, default is 2
          --refs-path REFS_PATH
                                set refs path, default is "./refs"
          --reveal              reveal refs (warning: this will potentially write
                                sensitive data)
          --embed-refs          embed ref contents
          --inventory-path INVENTORY_PATH
                                set inventory path, default is "./inventory"
          --cache, -c           enable compilation caching to .kapitan_cache and
                                dependency caching to .dependency_cache, default is
                                False
          --cache-paths PATH [PATH ...]
                                cache additional paths to .kapitan_cache, default is
                                []
          --ignore-version-check
                                ignore the version from .kapitan
          --use-go-jsonnet      use go-jsonnet
          --compose-target-name   Create same subfolder structure from inventory/targets
                                inside compiled folder
          --schemas-path SCHEMAS_PATH
                                set schema cache path, default is "./schemas"
          --yaml-multiline-string-style STYLE, -L STYLE
                                set multiline string style to STYLE, default is
                                'double-quotes'
          --yaml-dump-null-as-empty
                                dumps all none-type entries as empty, default is
                                dumping as 'null'
          --targets TARGET [TARGET ...], -t TARGET [TARGET ...]
                                targets to compile, default is all
          --labels [key=value ...], -l [key=value ...]
                                compile targets matching the labels, default is all
        ```
