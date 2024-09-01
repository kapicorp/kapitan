# Schema Validation (for k8s)

If a yaml/json output is to be used as k8s manifest, users may specify its kind and have kapitan validate its structure during `kapitan compile`.
The plan is to have this validation feature extendable to other outputs as well, such as terraform.

Author: @yoshi-1224

## Specification

The following inventory will validate the structure of Kubernetes Service manifest file in <output_path>.

```yaml
parameters:
  kapitan:
    validate:
       - output_type: kubernetes.service
         version: 1.6.6
         output_path: relative/path/in/target
```

`version` parameter is optional: if omitted, the version will be set to the stable release of kubernetes (tbc).

## Implementation

- The schemas will be downloaded by requests from
[this repository](https://raw.githubusercontent.com/garethr/kubernetes-json-schema/master/v1.6.6-standalone/deployment.json).
- Caching of schema will also be implemented.

### Dependencies

- [jsonschema](https://pypi.org/project/jsonschema/) to validate the output yaml/json against the correct schema
