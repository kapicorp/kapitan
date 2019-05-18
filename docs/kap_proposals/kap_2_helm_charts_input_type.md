# Helm Charts Input Type

This will allow kapitan, during compilation, to overwrite the values in user-specified helm charts using its inventory by calling the Go & Sprig template libraries. The helm charts can be specified via local path, and users may download the helm chart via [external-dependency feature](./kap_1_external_dependencies.md) (of http[s] type).

Author: @yoshi-1224

## Specification

This will run after the fetching of the external dependencies takes place, such that users can simultaneously specify the fetch as well as the import of a helm chart dependency.

### Semantics

TBC

## Implementation details

C-binding between Helm (Go) and Kapitan (Python) will be created. Helm makes use of two template libraries, namely, text/template and Sprig. The code for `helm template` command will be converted into shared object (.so) using CGo, which exposes C interface that kapitan (i.e. CPython) could use.  

### Dependencies

- (possibly) [pybindgen](https://pypi.org/project/PyBindGen/)
