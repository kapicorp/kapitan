# kapitan validate

Validates the schema of compiled output. Validate options are specified in the inventory under `parameters.kapitan.validate`. Supported types are:

- [kubernetes manifests](#Kubernetes-manife)

### Usage

1. Manually via command line after compile:

   ```
   $ kapitan validate
   ```

2. Automatically, together with compile:

   ```
   $ kapitan compile --validate
   ```

### Kubernetes manifests

#### Overview

Kubernetes resources are identified by their `kind`. For example, they are:

- service
- deployment
- statefulset

The manifest for each kind has certain restrictions such as required properties. Using kapitan, you can validate against the schemas to confirm that your compiled output indeed is a valid kubernetes manifest.

First time they are used, the schemas for kubernetes manifests are dynamically downloaded from https://kubernetesjsonschema.dev. Those schemas will be cached into `./schemas/` by default, which can be modified using `--schemas-path` option. However, it is recommended to use `.kapitan` configuration as follows to avoid the need of typing down this option for every command: 

```shell
$ cat .kapitan
# other options abbreviated for clarity
validate:
  schemas-path: custom/schemas/cache/path
```

#### Example

Refer to the `minikube-es` inventory in [kapitan inventory](#kapitan-inventory). To validate the schema of the compiled StatefulSet manifest at `compiled/minikube-es/manifests/es-client.yml` (created by `components/elasticsearch/main.jsonnet`), add `kapitan.validate` parameters in `minikube-es` inventory:

```yaml
kapitan:
  vars:
    target: ${target_name}
    namespace: ${target_name}
  compile:
  - output_path: manifests
    input_type: jsonnet
    input_paths:
      - components/elasticsearch/main.jsonnet

    ### other inputs abbreviated for clarity ###
  validate:
  - output_paths:
      - manifests/es-client.yml
    type: kubernetes
    kind: statefulset # note that it is in lowercase
    version: 1.14.0 # optional, defaults to 1.14.0
```

Then run:

```
$ kapitan validate -t minikube-es

invalid 'statefulset' manifest at ./compiled/minikube-es/manifests/es-client.yml
['spec'] 'selector' is a required property
```

