# :kapitan-logo: Kapitan: Advanced configuration management tool

![Unit Tests](https://github.com/kapicorp/kapitan/actions/workflows/test.yml/badge.svg)
![Pyhton version](https://img.shields.io/github/pipenv/locked/python-version/kapicorp/kapitan.svg)
![Downloads](https://img.shields.io/pypi/dm/kapitan)
![Docker Pulls](https://img.shields.io/docker/pulls/kapicorp/kapitan)
[![Docker](https://github.com/kapicorp/kapitan/workflows/Docker%20Build%20and%20Push/badge.svg)](https://github.com/kapicorp/kapitan/actions?query=workflow%3A%22Docker+Build+and+Push%22)
[![Releases](https://img.shields.io/github/release/kapicorp/kapitan.svg)](https://github.com/kapicorp/kapitan/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/kapicorp/kapitan/latest.svg)](https://hub.docker.com/r/kapicorp/kapitan)

**`Kapitan`** aims to be your *one-stop tool* to help you manage the ever growing complexity of your configurations.

:fontawesome-brands-slack: Join the community [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3)

## Why do I need **Kapitan**? 

> I use [`Helm`](https://helm.sh)/[`Kustomize`](https://kustomize.io/)/bring-your-own-tool

**Kapitan** allows you to brings all your configuration needs under one home, creating a uniform way to manage your configuration that no other tool provides.

[Longer answer](FAQ.md#why-do-i-need-kapitan)


### Dazzle me with a demo




## Install Kapitan

### Docker (recommended)

```shell
docker run -t --rm -v $(pwd):/src:delegated kapicorp/kapitan -h
```

On Linux you can add `-u $(id -u)` to `docker run` to preserve file permissions.

### Pip

Kapitan needs Python 3.6.

#### Install Python 3.6

* Linux: `sudo apt-get update && sudo apt-get install -y python3.6-dev python3-pip python3-yaml`
* Mac: `brew install python3 libyaml`

#### Install Kapitan

User (`$HOME/.local/lib/python3.6/bin` on Linux or `$HOME/Library/Python/3.6/bin` on macOS):

```shell
pip3 install --user --upgrade kapitan
```

System-wide (not recommended):

```shell
sudo pip3 install --upgrade kapitan
```


## Credits

* [Jsonnet](https://github.com/google/jsonnet)
* [Jinja2](http://jinja.pocoo.org/docs/2.9/)
* [reclass](https://github.com/salt-formulas/reclass)


## Related projects

* [Tesoro](https://github.com/kapicorp/tesoro) - Kubernetes Admission Controller for Kapitan Secrets
* [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) - Reference repository to get started
* [sublime-jsonnet-syntax](https://github.com/gburiola/sublime-jsonnet-syntax) - Jsonnet syntax highlighting for Sublime Text
* [language-jsonnet](https://github.com/google/language-jsonnet) - Jsonnet syntax highlighting for Atom
* [vim-jsonnet](https://github.com/google/vim-jsonnet) - Jsonnet plugin for Vim (requires a vim plugin manager)

## Community

* Join us on **kubernetes.slack.com** [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3)([**Get invited**](https://kubernetes.slack.com))
* **Follow us on Twitter** [@kapitandev](https://twitter.com/kapitandev/).
* **Website** [**`https://kapitan.dev`**](https://kapitan.dev)
* **Mailing List** [kapitan-discuss@googlegroups.com](mailto:kapitan-discuss@googlegroups.com)([**Subscribe**](https://groups.google.com/g/kapitan-discuss))
## Resources
* **Main Blog, articles and tutorials**: [Kapitan Blog](https://medium.com/kapitan-blog)
* [**Generators**](https://medium.com/kapitan-blog/keep-your-ship-together-with-kapitan-d82d441cc3e7) and reference kapitan repository: [Kapitan Reference](https://github.com/kapicorp/kapitan-reference)
* [Kapitan Reference](https://github.com/kapicorp/kapitan-reference): our reference repository to get started with Kapitan.