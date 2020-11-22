# Kapitan

Generic templated configuration management for GitOps, Kubernetes, Terraform and other things.

[![Build Status](https://travis-ci.org/deepmind/kapitan.svg?branch=master)](https://travis-ci.org/deepmind/kapitan)
![](https://img.shields.io/github/pipenv/locked/python-version/deepmind/kapitan.svg)
![](https://img.shields.io/pypi/dm/kapitan)
![](https://img.shields.io/docker/pulls/deepmind/kapitan)
[![Docker](https://github.com/deepmind/kapitan/workflows/Docker%20Build%20and%20Push/badge.svg)](https://github.com/deepmind/kapitan/actions?query=workflow%3A%22Docker+Build+and+Push%22)
[![Releases](https://img.shields.io/github/release/deepmind/kapitan.svg)](https://github.com/deepmind/kapitan/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/deepmind/kapitan/latest.svg)](https://hub.docker.com/r/deepmind/kapitan)

Kapitan is the tool to help you manage the complexity of your configuration using an inventory and a choice of templates like [generators](https://medium.com/kapitan-blog/keep-your-ship-together-with-kapitan-d82d441cc3e7), jsonnet, [kadet](https://github.com/deepmind/kapitan/pull/190), jinja2 and helm.

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

<img src="./docs/images/kapitan_logo.png" width="250">

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

### [Jsonnet](https://jsonnet.org/) or [Kadet](https://github.com/deepmind/kapitan/pull/190) templates backends
For more complex scenarios, you have a choice of directly using our 2 main templating engines.

You can use either [Jsonnet](https://jsonnet.org/) (tapping into an ever growing number of libraries and examples) or our Python based [Kadet](https://github.com/deepmind/kapitan/pull/190) to create json/yaml based configurations (e.g. Kubernetes, Terraform);

### [Jinja2](http://jinja.pocoo.org/)
Good old Jinja to create text based templates for scripts and documentation; Don't underestimate the power of this very simple approach to create templated scripts and documentation!

### [Kapitan Declarative Secrets](https://medium.com/kapitan-blog/declarative-secret-management-for-gitops-with-kapitan-b3c596eab088)
Use Kapitan to securely generate and manage secrets with GPG, AWS KMS, gCloud KMS and Vault.

Use [Tesoro](https://github.com/kapicorp/tesoro), our Kubernetes Admission Controller, to complete your integration with Kubernetes for secure secret decryption on-the-fly.

## Quickstart

See https://kapitan.dev/#quickstart

## Documentation

See https://kapitan.dev/ or `docs/README.md` in the source code.

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
