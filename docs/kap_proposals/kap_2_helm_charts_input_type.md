# Helm Charts Input Type

This will allow kapitan, during compilation, to overwrite the values in user-specified helm charts using its inventory by calling the Go & Sprig template libraries. The helm charts can be specified via local path, and users may download the helm chart via [external-dependency feature](./kap_1_external_dependencies.md) (of http[s] type).

Author: @yoshi-1224

## Specification

This feature basically follows the `helm template` command available.  
This will run after the fetching of the external dependencies takes place, such that users can simultaneously specify the fetch as well as the import of a helm chart dependency.

### Semantics

```yaml
kapitan:
  compile:
    - input_type: helm
      input_path: <path_to_chart_dir> 
      output_path: <output_path>
      set-file:
        - <optional_file_path>
        - ...
      values_file: <optional_values_file>
      namespace: <optional_namespace>
      
```

This mostly maps to the options available to `helm template` command (refer to [here](https://helm.sh/docs/helm/#helm-template)).

## Implementation details

C-binding between Helm (Go) and Kapitan (Python) will be created. Helm makes use of two template libraries, namely, text/template and Sprig. The code for `helm template` command will be converted into shared object (.so) using CGo, which exposes C interface that kapitan (i.e. CPython) could use.
The source code for `helm template` command is found [here](https://github.com/helm/helm/blob/master/cmd/helm/template.go). This file will be modified to

1. remove redundant options
2. expose C-interface for Kapitan

### Dependencies

- (possibly) [pybindgen](https://pypi.org/project/PyBindGen/)
