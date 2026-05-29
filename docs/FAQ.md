---
comments: true
title: "Kapitan FAQ"
description: "Find answers to frequently asked questions about Kapitan inventory, targets, classes, compilation, references, secrets, and supported input types."
---

# :kapitan-logo: **Kapitan FAQ**

## Why do I need Kapitan?

See the blog post [Why do I need **Kapitan**?](pages/blog/posts/2022-12-04.md#why-do-i-need-kapitan) for a detailed explanation of the problems Kapitan solves, including configuration sprawl, duplication across environments, and secrets management.

## What is the Kapitan inventory?

The [inventory](pages/inventory/introduction.md) is a hierarchical YAML structure that captures all the data you want to make available to Kapitan's templating engines. It is divided into [targets](pages/inventory/targets.md) (environments or deployments) and [classes](pages/inventory/classes.md) (reusable configuration fragments). Learn more in the [inventory introduction](pages/inventory/introduction.md).

## How do I install Kapitan?

The easiest way is via Docker:

```shell
docker run -t --rm -v $(pwd):/src:delegated kapicorp/kapitan -h
```

Or install with pip:

```shell
pip3 install --user --upgrade kapitan
```

See the [Getting Started](getting_started.md) page for full installation instructions.

## Which input type should I use?

It depends on your use case:

- **[Jsonnet](pages/input_types/jsonnet.md)** — structured data, Kubernetes manifests, JSON Schema validation
- **[Jinja](pages/input_types/jinja.md)** — scripts, documentation, text templates
- **[Kadet](pages/input_types/kadet.md)** — Python-based generation, reusable libraries
- **[Helm](pages/input_types/helm.md)** — rendering existing Helm charts
- **[Kustomize](pages/input_types/kustomize.md)** — patching Kubernetes manifests
- **[CUE](pages/input_types/cuelang.md)** — typed configuration with validation

## How does Kapitan manage secrets?

Kapitan uses [References](references.md) (formerly Secrets) to manage sensitive and dynamic values. Supported backends include GPG, AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault, and plain/base64 for non-sensitive data. See the [References documentation](references.md) for setup instructions.

## What is parameter interpolation?

Parameter interpolation lets you reference values defined elsewhere in the inventory using the `${variable:name}` syntax. This reduces duplication and makes configuration more maintainable. Read the [parameter interpolation guide](pages/inventory/parameters_interpolation.md) for details.

## How do I compile a target?

```shell
kapitan compile -t <target_name>
```

Without a target flag, Kapitan compiles all discovered targets. See the [`kapitan compile` CLI reference](pages/commands/kapitan_compile.md) for all options.

## Where can I find examples?

The [kapicorp/kapitan-reference](https://github.com/kapicorp/kapitan-reference) repository contains working examples for Kubernetes, Terraform, and more. You can also explore the [input type documentation](pages/input_types/introduction.md) for small, focused examples.

## Ask your question

Please use the comments facility below to ask your question.
