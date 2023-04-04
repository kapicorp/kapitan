# Kapitan: advanced configuration management tool

![Unit Tests](https://github.com/kapicorp/kapitan/actions/workflows/test.yml/badge.svg)
![Python Version](https://img.shields.io/pypi/pyversions/kapitan)
![Downloads](https://img.shields.io/pypi/dm/kapitan)
![Docker Pulls](https://img.shields.io/docker/pulls/kapicorp/kapitan)
[![Docker](https://github.com/kapicorp/kapitan/workflows/Docker%20Build%20and%20Push/badge.svg)](https://github.com/kapicorp/kapitan/actions?query=workflow%3A%22Docker+Build+and+Push%22)
[![Releases](https://img.shields.io/github/release/kapicorp/kapitan.svg)](https://github.com/kapicorp/kapitan/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/kapicorp/kapitan/latest.svg)](https://hub.docker.com/r/kapicorp/kapitan)

<img src="docs/images/kapitan_logo.png" width="25">


**`Kapitan`** aims to be your *one-stop tool* to help you manage the ever growing complexity of your configurations.

Join the community [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3)

## [**Official site**](https://kapitan.dev) <https://kapitan.dev>


## [**Quick Start**](https://kapitan.dev/kapitan_overview/#quickstart)

## Install Kapitan

### Docker (recommended)

```shell
docker run -t --rm -v $(pwd):/src:delegated kapicorp/kapitan -h
```

On Linux you can add `-u $(id -u)` to `docker run` to preserve file permissions.

### Pip

Kapitan needs Python 3.7.

#### Install Python 3.7

* Linux: `sudo apt-get update && sudo apt-get install -y python3.7-dev python3-pip python3-yaml git`
* Mac: `brew install python3 libyaml git libmagic`

#### Install Kapitan

User (`$HOME/.local/lib/python3.7/bin` on Linux or `$HOME/Library/Python/3.7/bin` on macOS):

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

## Related projects

* [Tesoro](https://github.com/kapicorp/tesoro) - Kubernetes Admission Controller for Kapitan Secrets
* [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) - our reference repository to get started with Kapitan
