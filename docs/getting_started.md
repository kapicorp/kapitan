# :kapitan-logo: **Installation**

## Setup your project

Once you have installed *Kapitan* (see #installation-methods), you can easily initialise your project with:

```
kapitan init --directory $HOME/kapitan-templates
```

??? note "Example output"
    ```
    Initialising skeleton from https://github.com/kapicorp/kapitan-reference.git@copier in $HOME/kapitan-templates
    🎤 What version of Kapitan
    0.32.0

    Copying from template version 0.0.0.post140.dev0+aaeecf6
        create  .
        create  .kapitan
        create  .github
        create  .github/workflows
        create  .github/workflows/integration-test.yml
        create  .github/workflows/pre-commit.yml
        create  .gitignore
        create  system
        create  system/sources
        [OMITTED]
        create  .pre-commit-config.yaml
        create  README.md
        create  kapitan

    > Running task 1 of 2: git init --quiet
    > Running task 2 of 2: ./kapitan compile
    Dependency https://github.com/kapicorp/generators.git: saved to system/lib
    Dependency https://github.com/kapicorp/generators.git: saved to system/generators/kubernetes
    Dependency https://github.com/kapicorp/generators.git: saved to system/generators/terraform
    Rendered inventory (2.09s)
    Compiled tutorial (0.16s)
    ```


## Installation methods

We provide you with different easy ways to install `kapitan`. Please pick one of the following methods

!!! success "recommended"
    ### Docker
    ![Docker Pulls](https://img.shields.io/docker/pulls/kapicorp/kapitan)
    [![Docker Image Size](https://img.shields.io/docker/image-size/kapicorp/kapitan/latest.svg)](https://hub.docker.com/r/kapicorp/kapitan)
    [![Docker](https://github.com/kapicorp/kapitan/workflows/Docker%20Build%20and%20Push/badge.svg)](https://github.com/kapicorp/kapitan/actions?query=workflow%3A%22Docker+Build+and+Push%22)


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
    sudo apt-get update && sudo apt-get install -y python3.8-dev python3-pip python3-yaml
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
        `kapitan` will be installed in `$HOME/.local/lib/python3.7/bin`

    ```shell
    pip3 install --user --upgrade kapitan
    ```

=== "Mac"

    !!! note ""
        `kapitan` will be installed in `$HOME/Library/Python/3.7/bin`

    ```shell
    pip3 install --user --upgrade kapitan
    ```


##### System-wide

!!! attention "not recommended"

    ```shell
    sudo pip3 install --upgrade kapitan
    ```
