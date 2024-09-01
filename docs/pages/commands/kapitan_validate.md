# :kapitan-logo: **CLI Reference** | `kapitan validate`

## `kapitan validate`

Validates the schema of compiled output. Validate options are specified in the inventory under `parameters.kapitan.validate`. Supported types are:

### Usage

=== "standalone"
    !!! example ""

        ```shell
        kapitan validate
        ```

        ??? example "click to expand output"
            ```shell
            created schema-cache-path at ./schemas
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_secret.yml
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_service_jsonnet.yml
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_service_simple.yml
            ```
=== "manual with `kapitan compile`"
    !!! example ""
        ```shell
        kapitan compile --validate
        ```

        ??? example "click to expand output"
            ```shell
            Rendered inventory (0.27s)
            Compiled labels (0.23s)
            Compiled removal (0.00s)
            Compiled busybox (0.24s)
            Compiled minikube-nginx-jsonnet (0.49s)
            Compiled minikube-nginx-kadet (0.25s)
            Compiled minikube-mysql (0.59s)
            Compiled minikube-es (1.17s)
            Compiled all-glob (1.55s)
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_secret.yml
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_service_jsonnet.yml
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_service_simple.yml
            ```

=== "automatic with `.kapitan` dotfile"

    You can leverage the `.kapitan` dotfile to make sure validate runs every time you run compile.



    !!! example ""
        !!! quote "example `.kapitan`"
            ```yaml
            ...

            compile:
              validate: true
            ```

        The `validate` command will now be implied for every compile run
        ```shell
        kapitan compile
        ```

        ??? example "click to expand output"
            ```shell
            Rendered inventory (0.27s)
            Compiled labels (0.23s)
            Compiled removal (0.00s)
            Compiled busybox (0.24s)
            Compiled minikube-nginx-jsonnet (0.49s)
            Compiled minikube-nginx-kadet (0.25s)
            Compiled minikube-mysql (0.59s)
            Compiled minikube-es (1.17s)
            Compiled all-glob (1.55s)
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_secret.yml
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_service_jsonnet.yml
            Validation: manifest validation successful for ./compiled/minikube-mysql/manifests/mysql_service_simple.yml
            ```

### Kubernetes Setup

**Kubernetes** has different resource kinds, for instance:

- `service`
- `deployment`
- `statefulset`

 **Kapitan** has built in support for validation of **Kubernetes** kinds, and automatically integrates with <https://kubernetesjsonschema.dev>. See [github.com/instrumenta/kubernetes-json-schema](https://github.com/instrumenta/kubernetes-json-schema) for more informations.

!!! info

    **Kapitan** will automatically download the schemas for Kubernetes Manifests directly from <https://kubernetesjsonschema.dev>

    By default, the schemas are cached into `./schemas/`, which can be modified with the `--schemas-path` option.

    !!! tip "override permanently `schema-path`"
          Remember to use the `.kapitan` dotfile configuration to override permanently the `schema-path` location.


          ```shell
          $ cat .kapitan
          # other options abbreviated for clarity
          validate:
            schemas-path: custom/schemas/cache/path
          ```

#### Example

Refer to the `mysql` example.

```yaml hl_lines="2-6" title="kubernetes/inventory/classes/component/mysql.yml"
--8<-- "kubernetes/inventory/classes/component/mysql.yml:19:30"
```

1. **`type`** | currently only **Kubernetes** is supported
2. **`output_paths`** | list of files to validate
3. **`kind`** | a **Kubernetes** resource kind
4. **`version`** | a Kubernetes API version, defaults to **`1.14.0`**
