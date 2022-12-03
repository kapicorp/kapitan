# :kapitan-logo: **Kapitan: Keep your ship together**

![GitHub Sponsors](https://img.shields.io/github/sponsors/kapicorp?style=for-the-badge)
![GitHub Stars](https://img.shields.io/github/stars/kapicorp/kapitan?style=for-the-badge)

**`Kapitan`** aims to be your *one-stop tool* to help you manage the ever growing complexity of your configurations.

* :fontawesome-brands-slack: Join the community [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3)
* :fontawesome-brands-github: Help us grow: [give us a star](https://github.com/kapicorp/kapitan/stargazers) or even better [sponsor our project](/contributing/#sponsor-kapitan)

## Why do I need **Kapitan**? 

> I use [`Helm`](https://helm.sh)/[`Kustomize`](https://kustomize.io/)/that-new-kid-on-the-block

**Kapitan** allows you to bring all your configuration needs under one home, creating a uniform way to manage your configuration that no other tool provides. Seamlessly manage configurations for Kubernetes, Terraform and any other application. Integrate with Helm (and even Kustomize). Safely store your secrets using a range of Secret Backends

[Longer answer](pages/blog/2022-12-04.md#why-do-i-need-kapitan)

!!! info
        We are working hard to update all our documentation. Please reach out if you notice something that needs improving or you have other questions or comments. 

## Dazzle me with a demo

![demo](images/kapitan-demo.gif)

## Install Kapitan

[![Releases](https://img.shields.io/github/release/kapicorp/kapitan.svg)](https://github.com/kapicorp/kapitan/releases)

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

![Python version](https://img.shields.io/github/pipenv/locked/python-version/kapicorp/kapitan.svg)
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

## Related projects

* [Tesoro](https://github.com/kapicorp/tesoro) - Kubernetes Admission Controller for Kapitan Secrets
* [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) - our reference repository to get started with Kapitan
