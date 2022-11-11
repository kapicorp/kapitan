# Modularize Kapitan

Kapitan is packaged in PYPI and as a binary along with all its dependencies. Adding an extra key/security backend means that we need to ship another dependency with that PYPI package, making deploying changes more complicated. This project would modularize kapitan into core dependencies and extra modules.

## Usage

```sh
pip3 install --user kapitan # to install only core dependencies
Pip3 install --user kapitan[gkms] ​# gkms is the module
```

## Implementation

- The main module includes the essential kapitan dependencies and reclass dependencies, which will be included in the ​requirement.txt​ file.
- The extra module [pypi extras](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies) will be defined in the `s​etup.py`​ file.
- The extra dependencies are of secret backends like (AWS Key backend, Google KMS Key backend, Vault Key backend etc.) and Helm support.
