# Kapitan: Generic templated configuration management for Kubernetes, Terraform and other things

[![Build Status](https://travis-ci.org/deepmind/kapitan.svg?branch=master)](https://travis-ci.org/deepmind/kapitan)

Kapitan is a tool to manage complex deployments using jsonnet, [kadet (alpha)](https://github.com/deepmind/kapitan/pull/190) and jinja2.

Use Kapitan to manage your Kubernetes manifests, your documentation, your Terraform configuration or even simplify your scripts.

## Community
* **Main Blog, articles and tutorials**: [Kapitan Blog](https://medium.com/kapitan-blog)
* **Slack** [`#kapitan`](https://kubernetes.slack.com)
* **Website** [**`https://kapitan.dev`**](https://kapitan.dev)
* **Mailing List** [kapitan-discuss@googlegroups.com](mailto:kapitan-discuss@googlegroups.com)
* **London Meetup Group** [London Kapitan Meetup](https://www.meetup.com/London-Kapitan-Meetup/)


How is it different from [`Helm`](https://github.com/kubernetes/helm)? Please look at our [FAQ](https://kapitan.dev/#faq)!

<img src="./docs/images/kapitan_logo.png" width="250">

# Main Features

* Use the Inventory as the single source of truth to tie together deployments, resources and documentation. [based on reclass](https://github.com/salt-formulas/reclass)
* Use [Jsonnet](https://jsonnet.org/) or [Kadet (alpha)](https://github.com/deepmind/kapitan/pull/190) to create json/yaml based configurations (e.g. Kubernetes, Terraform);
* Use [Jinja2](http://jinja.pocoo.org/) to create text based templates for scripts and documentation;
* Manage secrets with GPG, AWS KMS or gCloud KMS and define who can access them, without compromising collaboration with other users.
* Create dynamically generated documentation about a single deployment (i.e. ad-hoc instructions) or all deployments at once (i.e. global state of deployments)

# Quickstart

See https://kapitan.dev/#quickstart

# Documentation

See https://kapitan.dev/ or `docs/README.md` in the source code.

# Credits

* [Jsonnet](https://github.com/google/jsonnet)
* [Jinja2](http://jinja.pocoo.org/docs/2.9/)
* [reclass](https://github.com/salt-formulas/reclass)

# Related projects

* [sublime-jsonnet-syntax](https://github.com/gburiola/sublime-jsonnet-syntax) - Jsonnet syntax highlighting for Sublime Text
* [language-jsonnet](https://github.com/google/language-jsonnet) - Jsonnet syntax highlighting for Atom
* [vim-jsonnet](https://github.com/google/vim-jsonnet) - Jsonnet plugin for Vim (requires a vim plugin manager)
