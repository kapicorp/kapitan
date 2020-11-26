# Kapitan: Generic templated configuration management for Kubernetes, Terraform and other things

[![Build Status](https://travis-ci.org/deepmind/kapitan.svg?branch=master)](https://travis-ci.org/deepmind/kapitan)
![](https://img.shields.io/github/pipenv/locked/python-version/deepmind/kapitan.svg)
![](https://img.shields.io/pypi/dm/kapitan)
![](https://img.shields.io/docker/pulls/deepmind/kapitan)
[![Docker](https://github.com/deepmind/kapitan/workflows/Docker%20Build%20and%20Push/badge.svg)](https://github.com/deepmind/kapitan/actions?query=workflow%3A%22Docker+Build+and+Push%22)
[![Releases](https://img.shields.io/github/release/deepmind/kapitan.svg)](https://github.com/deepmind/kapitan/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/deepmind/kapitan/latest.svg)](https://hub.docker.com/r/deepmind/kapitan)

Kapitan is the tool to help you manage the complexity of your configuration using an inventory and a choice of templates like [generators](https://medium.com/kapitan-blog/keep-your-ship-together-with-kapitan-d82d441cc3e7), jsonnet, [kadet](https://kapitan.dev/compile/#kadet), jinja2 and helm.

Use Kapitan to build an inventory which you can then use to drive templates for your Kubernetes manifests, your documentation, your Terraform configuration or even simplify your scripts.

## Community
* **Main Blog, articles and tutorials**: [Kapitan Blog](https://medium.com/kapitan-blog)
* [**Generators**](https://medium.com/kapitan-blog/keep-your-ship-together-with-kapitan-d82d441cc3e7) and reference kapitan repository: [Kapitan Reference](https://github.com/kapicorp/kapitan-reference)
* [Kapitan Reference](https://github.com/kapicorp/kapitan-reference): our reference repository to get started with Kapitan.
* **Slack** [`#kapitan`](https://kubernetes.slack.com)
* **Twitter** [@kapitandev](https://twitter.com/kapitandev/) on Twitter. Follow us and share our tweets!
* **Website** [**`https://kapitan.dev`**](https://kapitan.dev)
* **Mailing List** [kapitan-discuss@googlegroups.com](mailto:kapitan-discuss@googlegroups.com)

How is it different from [`helm`](https://github.com/kubernetes/helm) and [`kustomize`](https://github.com/kubernetes-sigs/kustomize)? Please look at our [FAQ](https://kapitan.dev/#faq)!

<img src="docs/images/kapitan_logo.png" width="250">

## Key Concepts

### Inventory
The inventory is the heart of Kapitan. 
Using simple reusable `yaml` files (classes), you can represent as a ***single source of truth*** 
everything that matters in your setup, for instance:
 * kubernetes `components` definitions
 * terraform resources
 * business concepts
 * documentation and tooling
 * ...anything else you want!
  
 Once you have it defined, you can reuse this data to feed into any of the many templating backends available to Kapitan.
 
### [**Generators**](https://medium.com/kapitan-blog/keep-your-ship-together-with-kapitan-d82d441cc3e7)
The simplest way to get started with Kapitan. 
Generators are ***universal templates*** that are a simplified way to generate configuration 
files (for instance, Kubernetes manifests) without using any templating at all. 
> Check out our reference repository to get started:  [Kapitan Reference](https://github.com/kapicorp/kapitan-reference)

> Read our blog post [**Keep your ship together with Kapitan**](https://medium.com/kapitan-blog/keep-your-ship-together-with-kapitan-d82d441cc3e7) 

### [Jsonnet](https://jsonnet.org/) or [Kadet](https://kapitan.dev/compile/#kadet) templates backends
For more complex scenarios, you have a choice of directly using our 2 main templating engines.

You can use either [Jsonnet](https://jsonnet.org/) (tapping into an ever growing number of libraries and examples) or our Python based [Kadet](https://kapitan.dev/compile/#kadet) to create json/yaml based configurations (e.g. Kubernetes, Terraform);

### [Jinja2](http://jinja.pocoo.org/)
Good old Jinja to create text based templates for scripts and documentation; Don't underestimate the power of this very simple approach to create templated scripts and documentation!

### [Kapitan Declarative Secrets](https://medium.com/kapitan-blog/declarative-secret-management-for-gitops-with-kapitan-b3c596eab088)
Use Kapitan to securely generate and manage secrets with GPG, AWS KMS, gCloud KMS and Vault.

Use [Tesoro](https://github.com/kapicorp/tesoro), our Kubernetes Admission Controller, to complete your integration with Kubernetes for secure secret decryption on-the-fly.

## Quickstart

#### Docker (recommended)

```
docker run -t --rm -v $(pwd):/src:delegated deepmind/kapitan -h
```

On Linux you can add `-u $(id -u)` to `docker run` to preserve file permissions.

For CI/CD usage, check out [CI.md](docs/CI.md)

#### Pip

Kapitan needs Python 3.6.

**Install Python 3.6:**

 * Linux: `sudo apt-get update && sudo apt-get install -y python3.6-dev python3-pip python3-yaml`
 * Mac: `brew install python3 libyaml`

**Install Kapitan:**

User (`$HOME/.local/lib/python3.6/bin` on Linux or `$HOME/Library/Python/3.6/bin` on macOS):

```shell
pip3 install --user --upgrade kapitan
```

System-wide (not recommended):

```shell
sudo pip3 install --upgrade kapitan
```

#### Standalone binary

From v0.24.0, kapitan is also available as a standalone binary which you can download from the [releases page](https://github.com/deepmind/kapitan/releases). The platform currently supported is Linux amd64.

## Example

The example below _compiles_ 2 targets inside the `examples/kubernetes` folder.
Each target represents a different namespace in a minikube cluster.

These targets generate the following resources:

* Kubernetes `Namespace` for the targets
* Kubernetes `StatefulSet` for ElasticSearch Master node
* Kubernetes `StatefulSet` for ElasticSearch Client node
* Kubernetes `StatefulSet` for ElasticSearch Data node
* Kubernetes `Service` to expose ElasticSearch discovery port
* Kubernetes `Service` to expose ElasticSearch service port
* Kubernetes `StatefulSet` for MySQL
* Kubernetes `Service` to expose MySQL service port
* Kubernetes `Secret` for MySQL credentials
* Scripts to configure kubectl context to control the targets and helpers to apply/delete objects.
* Documentation

![demo](docs/images/demo.gif)

```shell
$ cd examples/kubernetes

$ kapitan compile
Compiled minikube-mysql
Compiled minikube-es
```

## Documentation

### Getting Started

- [Kapitan Overview](docs/kapitan_overview.md)
- [Understanding inventory](docs/inventory.md)
- [Compile operation](docs/compile.md)

### Kapitan features

- [References (formerly secrets)](docs/secrets.md)
- [Manifest validation](docs/validate.md)
- [External dependencies management](docs/external_dependencies.md)

### Miscellaneous

- [Usage](docs/usage.md)
- [Continuous Integration](docs/CI.md)
- [Set up kapitan on older Python systems](docs/pyenv-scl.md)

### Examples

- [Kubernetes](docs/example-kubernetes.md)

## Credits

* [Jsonnet](https://github.com/google/jsonnet)
* [Jinja2](http://jinja.pocoo.org/docs/2.9/)
* [reclass](https://github.com/salt-formulas/reclass)

## FAQ

### Why do we prefer Kapitan to `Helm`?

Before developing Kapitan, we turned to [`Helm`](https://github.com/kubernetes/helm) in an attempt to improve our old Jinja based templating system.

We quickly discovered that `Helm` did not fit well with our workflow, for the following reasons (which were true at the time of the evaluation):

* `Helm` uses Go templates to define Kubernetes (yaml) manifests. We were already unsatisfied by using Jinja and we did not see a huge improvement from our previous system, the main reason being: YAML files are not suitable to be managed by text templating frameworks.
* `Helm` does not have a solution for sharing values across charts, if not through subcharts. We wanted to be able to have one single place to define all values for all our templates. Sharing data between charts felt awkward and complicated.
* `Helm` is component/chart based. We wanted to have something that would treat all our deployments as a whole.
* We did not fancy the dependency on the tiller.

In short, we feel `Helm` is trying to be `apt-get` for Kubernetes charts, while we are trying to take you further than that.

### Why do I need Kapitan?
With Kapitan, we worked to de-compose several problems that most of the other solutions are treating as one.

1) ***Kubernetes manifests***: We like the jsonnet approach of using json as the working language. Jsonnet allows us to use inheritance and composition, and hide complexity at higher levels.

2) ***Configuration files***: Most solutions will assume this problem is solved somewhere else. We feel Jinja (or your template engine of choice) have the upper hand here.

3) ***Hierarchical inventory***: This is the feature that sets us apart from other solutions. We use the inventory (based on [reclass](https://github.com/salt-formulas/reclass)) to define variables and properties that can be reused across different projects/deployments. This allows us to limit repetition, but also to define a nicer interface with developers (or CI tools) which will only need to understand YAML to operate changes.

4) ***Secrets***: We manage most of our secrets with kapitan using the GPG, Google Cloud KMS and AWS KMS integrations. Keys can be setup per class, per target or shared so you can easily and flexibly manage access per environment. They can also be dynamically generated on compilation, if you don't feel like generating random passwords or RSA private keys, and they can be referenced in the inventory like any other variables. We have plans to support other providers such as Vault, in addition to GPG, Google Cloud KMS and AWS KMS.

5) ***Canned scripts***: We treat scripts as text templates, so that we can craft pre-canned scripts for the specific target we are working on. This can be used for instance to define scripts that setup clusters, contexts or allow running kubectl with all the correct settings. Most other solutions require you to define contexts and call kubectl with the correct settings. We take care of that for you. Less ambiguity, fewer mistakes.

6) ***Documentation***: We also use templates to create documentation for the targets we deploy. Documentation lived alongside everything else and it is treated as a first class citizen.
We feel most other solutions are pushing the limits of their capacity in order to provide for the above problems.
Helm treats everything as a text template, while jsonnet tries to do everything as json.
We believe that these approaches can be blended in a powerful new way, glued together by the inventory.


## Related projects

* [Tesoro](https://github.com/kapicorp/tesoro) - Kubernetes Admission Controller for Kapitan Secrets
* [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) - Reference repository to get started
* [sublime-jsonnet-syntax](https://github.com/gburiola/sublime-jsonnet-syntax) - Jsonnet syntax highlighting for Sublime Text
* [language-jsonnet](https://github.com/google/language-jsonnet) - Jsonnet syntax highlighting for Atom
* [vim-jsonnet](https://github.com/google/vim-jsonnet) - Jsonnet plugin for Vim (requires a vim plugin manager)
