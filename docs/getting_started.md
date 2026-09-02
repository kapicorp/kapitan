---
title: "Getting Started with Kapitan in Minutes"
description: "Install Kapitan with Docker or pip, clone a reference repository, and compile your first Kubernetes and infrastructure targets in minutes."
---

# :kapitan-logo: **Getting Started with Kapitan**

## Setup your installation

Using our reference repositories you can easily get started with **Kapitan**

### Examples repository

[kapicorp/kapitan-reference](https://github.com/kapicorp/kapitan-reference) repository is meant show you many working examples of things you can do with Kapitan.
You can use this to get familiar with **Kapitan**

```
$ git clone git@github.com:kapicorp/kapitan-reference.git kapitan-templates
$ cd kapitan-templates

$ ./kapitan compile
Compiled postgres-proxy (1.51s)
Compiled tesoro (1.70s)
Compiled echo-server (1.64s)
Compiled mysql (1.67s)
Compiled gke-pvm-killer (1.17s)
Compiled prod-sockshop (4.74s)
Compiled dev-sockshop (4.74s)
Compiled tutorial (1.68s)
Compiled global (0.76s)
Compiled examples (2.60s)
Compiled pritunl (2.03s)
Compiled sock-shop (4.36s)
```

### Minimal repository

> Using [cruft](https://cruft.github.io/cruft/) based cookiecutter

```shell
pip3 install cruft
```

```shell
cruft create http://github.com/kapicorp/kapitan-reference --checkout cookiecutter --no-input
Dependency https://github.com/kapicorp/generators.git: saved to system/lib
Dependency https://github.com/kapicorp/generators.git: saved to system/generators/kubernetes
Dependency https://github.com/kapicorp/generators.git: saved to system/generators/terraform
Rendered inventory (1.74s)
Compiled echo-server (0.14s)
```

## running **Kapitan**

!!! success "recommended"
    **`kapitan` wrapper script**
    If you use the provided repository, we already package a `kapitan` shell script that wraps the docker command to run **Kapitan**

    ```shell
    $ ./kapitan compile
    Compiled postgres-proxy (1.51s)
    Compiled tesoro (1.70s)
    Compiled echo-server (1.64s)
    Compiled mysql (1.67s)
    Compiled gke-pvm-killer (1.17s)
    Compiled prod-sockshop (4.74s)
    Compiled dev-sockshop (4.74s)
    Compiled tutorial (1.68s)
    Compiled global (0.76s)
    Compiled examples (2.60s)
    Compiled pritunl (2.03s)
    Compiled sock-shop (4.36s)
    ```

## Other installation methods

### Docker

[![Releases](https://img.shields.io/github/release/kapicorp/kapitan.svg)](https://github.com/kapicorp/kapitan/releases){: aria-label="GitHub releases"}

!!! success "recommended"
    **Docker**
    ![Docker Pulls](https://img.shields.io/docker/pulls/kapicorp/kapitan)
    [![Docker Image Size](https://img.shields.io/docker/image-size/kapicorp/kapitan/latest.svg)](https://hub.docker.com/r/kapicorp/kapitan){: aria-label="Docker image size"}
    [![Docker](https://github.com/kapicorp/kapitan/workflows/Docker%20Build%20and%20Push/badge.svg)](https://github.com/kapicorp/kapitan/actions?query=workflow%3A%22Docker+Build+and+Push%22){: aria-label="Docker Build and Push status"}


    === "Linux"

        ```shell
        alias kapitan="docker run -t --rm -u $(id -u) -v $(pwd):/src:delegated kapicorp/kapitan"
        kapitan -h
        ```

    === "Mac"

        ```shell
        alias kapitan="docker run -t --rm -v $(pwd):/src:delegated kapicorp/kapitan"
        kapitan -h
        ```

### Pip

#### Install Python

![Python version](https://img.shields.io/pypi/pyversions/kapitan)
![Unit Tests](https://github.com/kapicorp/kapitan/actions/workflows/test.yml/badge.svg)
=== "Linux"

    ```shell
    sudo apt-get update && sudo apt-get install -y python3-dev python3-pip python3-yaml
    ```

=== "Mac"

    ```shell
    brew install python3 libyaml
    ```

#### Install Kapitan using pip

![downloads](https://img.shields.io/pypi/dm/kapitan)

##### User

=== "Linux"

    !!! note ""
        `kapitan` will be installed in `$HOME/.local/lib/python3.x/bin`

    ```shell
    pip3 install --user --upgrade kapitan
    ```

=== "Mac"

    !!! note ""
        `kapitan` will be installed in `$HOME/Library/Python/3.x/bin`

    ```shell
    pip3 install --user --upgrade kapitan
    ```


##### System-wide

!!! attention "not recommended"

    ```shell
    sudo pip3 install --upgrade kapitan
    ```

#### Pre-release versions

Every merge to `master` is automatically published to PyPI as a PEP 440 pre-release. To install the latest development build:

=== "pip"

    ```shell
    pip3 install --user --upgrade --pre kapitan
    ```

=== "uv"

    ```shell
    uv tool install --upgrade --prerelease allow kapitan
    ```

=== "poetry"

    ```shell
    poetry add --allow-prereleases kapitan
    ```

---

## Next steps

- Learn the [Kapitan core concepts](pages/core_concepts.md): how inventory, targets, classes, and input types work together.
- Understand the [Kapitan inventory](pages/inventory/introduction.md): targets, classes, and parameter interpolation.
- Explore [input types](pages/input_types/introduction.md) such as [Jsonnet](pages/input_types/jsonnet.md), [Jinja](pages/input_types/jinja.md), [Kadet](pages/input_types/kadet.md), [Helm](pages/input_types/helm.md), and [Kustomize](pages/input_types/kustomize.md).
- Manage secrets and external values with [Kapitan References](references.md).
