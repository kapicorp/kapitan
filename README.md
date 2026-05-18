# Kapitan: Configuration Management for Kubernetes, Terraform, and Infrastructure

[![Test, Build and Publish docker image](https://github.com/kapicorp/kapitan/actions/workflows/test-build-publish.yml/badge.svg?branch=master&event=push)](https://github.com/kapicorp/kapitan/actions/workflows/test-build-publish.yml)
![Python Version](https://img.shields.io/pypi/pyversions/kapitan)
![Downloads](https://img.shields.io/pypi/dm/kapitan)
![Docker Pulls](https://img.shields.io/docker/pulls/kapicorp/kapitan)
[![Releases](https://img.shields.io/github/release/kapicorp/kapitan.svg)](https://github.com/kapicorp/kapitan/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/kapicorp/kapitan/latest.svg)](https://hub.docker.com/r/kapicorp/kapitan)

<img src="docs/images/kapitan_logo.png" width="25" alt="Kapitan logo">

**Kapitan** is an open source configuration management tool for **Kubernetes**, **Terraform**, and complex infrastructure systems. It helps teams generate, organize, reuse, and validate configuration across environments using an **inventory-driven model**, templates (**Jsonnet**, **Jinja2**, **Kadet**), and integrations with **Helm**, **Kustomize**, **CUE**, and external references.

Kapitan provides native **secrets management** (GPG, AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault) and is designed for **Platform Engineering** and **GitOps** workflows.

- **Documentation**: <https://kapitan.dev>
- **Community**: [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3) on Kubernetes Slack
- **Quick Start**: <https://kapitan.dev/getting_started/>

## What is Kapitan?

Kapitan lets you model infrastructure configuration with reusable **inventory classes** and **targets**, then compile that data into manifests, scripts, documentation, and Terraform resources. Instead of copying values across Helm values files, Kustomize overlays, and Terraform variables, you define everything once in the Kapitan inventory and let each input type generate the files it needs.

## Install Kapitan

### Docker (recommended)

```shell
docker run -t --rm -v $(pwd):/src:delegated kapicorp/kapitan -h
```

On Linux you can add `-u $(id -u)` to `docker run` to preserve file permissions.

### Pip

Kapitan needs Python 3.10 or newer.

#### Install Python 3

* Linux: `sudo apt-get update && sudo apt-get install -y python3-dev python3-pip python3-yaml git`
* Mac: `brew install python3 libyaml git`

#### Install Kapitan

User (`$HOME/.local/lib/python3.x/bin` on Linux or `$HOME/Library/Python/3.x/bin` on macOS):

```shell
pip3 install --user --upgrade kapitan
```

System-wide (not recommended):

```shell
sudo pip3 install --upgrade kapitan
```

## Build Kapitan

### Docker

To build a docker image for the architecture of your machine, run `docker build . -t you-kapitan-image`, and to build for a specific platform, add `--platform linux/arm64`.

To build a multi-platform image (as the CI does), follow [the docker multi-platform documentation](https://docs.docker.com/build/building/multi-platform/).

To build a docker image using a specific python version, run `docker build --build-arg PYTHON_BUILDER_VERSION=<python-version> . -t you-kapitan-image`. By default the Dockerfile is pinned using python 3.11 as the python builder version.

## Related projects

* [Tesoro](https://github.com/kapicorp/tesoro) - Kubernetes Admission Controller for Kapitan Secrets
* [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) - our reference repository to get started with Kapitan
