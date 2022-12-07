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

- `Service`
- `Deployment`
- `Statefulset`

 **Kapitan** has built in support for validation of **Kubernetes** kinds, and automatically integrates with [kapicorp/kubernetes-json-schema](https://github.com/kapicorp/kubernetes-json-schema)


!!! info

    **Kapitan** will automatically download the schemas for Kubernetes Manifests directly from [kapicorp/kubernetes-json-schema](https://github.com/kapicorp/kubernetes-json-schema)
    
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

```yaml hl_lines="2-12" title="kubernetes/inventory/classes/component/mysql.yml"
--8<-- "kubernetes/inventory/classes/component/mysql.yml:19:30"
```

1. **`type`** | currently only **Kubernetes** is supported
2. **`output_paths`** | list of paths to validate, with supports for glob patterns
3. **`fail_on_error`** | whether to fail compilation on error, defaults to **`True`**
4. **`version`** | a Kubernetes API version, defaults to **`1.26.0`**
5. **`verbose`** | whether to also print successful validations, defaults to **`False`**
6. **`exclude.kind`** | list of Kubernetes kinds to exclude.
7. **`exclude.paths`** | list of paths to exclude.
