# Kapitan: Configuration Management for Kubernetes, Terraform, and Infrastructure

[![Test, Build and Publish docker image](https://github.com/kapicorp/kapitan/actions/workflows/test-build-publish.yml/badge.svg?branch=master&event=push)](https://github.com/kapicorp/kapitan/actions/workflows/test-build-publish.yml)
[![Python Version](https://img.shields.io/pypi/pyversions/kapitan)](https://pypi.org/project/kapitan/)
[![Downloads](https://img.shields.io/pypi/dm/kapitan)](https://pypi.org/project/kapitan/)
[![Docker Pulls](https://img.shields.io/docker/pulls/kapicorp/kapitan)](https://hub.docker.com/r/kapicorp/kapitan)
[![Releases](https://img.shields.io/github/release/kapicorp/kapitan.svg)](https://github.com/kapicorp/kapitan/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/kapicorp/kapitan/latest.svg)](https://hub.docker.com/r/kapicorp/kapitan)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<img src="docs/images/kapitan_logo.png" width="25" alt="Kapitan logo">

**Kapitan** is an open source configuration management tool for **Kubernetes**, **Terraform**, and complex infrastructure systems. It helps teams generate, organize, reuse, and validate configuration across environments using an **inventory-driven model**, templates (**Jsonnet**, **Jinja2**, **Kadet**), and integrations with **Helm**, **Kustomize**, **CUE**, and external references.

Kapitan provides native **secrets management** (GPG, AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault) and is designed for **Platform Engineering** and **GitOps** workflows.

- **Website**: https://kapitan.dev
- **Documentation**: https://kapitan.dev/getting_started/
- **Community**: [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3) on Kubernetes Slack
- **Sponsor**: [GitHub Sponsors](https://github.com/sponsors/kapicorp)

---

## Quick start

The fastest way to try Kapitan is with the [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) repository:

```shell
git clone https://github.com/kapicorp/kapitan-reference.git kapitan-templates
cd kapitan-templates
./kapitan compile
```

For a minimal project from a cookiecutter template:

```shell
pip3 install cruft
cruft create https://github.com/kapicorp/kapitan-reference --checkout cookiecutter --no-input
```

## What is Kapitan?

Kapitan lets you model infrastructure configuration with reusable **inventory classes** and **targets**, then compile that data into manifests, scripts, documentation, and Terraform resources. Instead of copying values across Helm values files, Kustomize overlays, and Terraform variables, you define everything once in the Kapitan inventory and let each input type generate the files it needs.

## Install Kapitan

### Docker (recommended)

```shell
docker run -t --rm -v $(pwd):/src:delegated kapicorp/kapitan -h
```

On Linux, add `-u $(id -u)` to preserve file permissions.

### Pip

Kapitan requires Python 3.10 or newer.

```shell
pip3 install --user --upgrade kapitan
```

See the [full installation guide](https://kapitan.dev/getting_started/) for platform-specific steps.

## What Kapitan does

Kapitan turns a hierarchical **inventory** and a set of **input templates** into compiled configuration files ready for deployment.

1. Define reusable **classes** and per-environment **targets** in YAML.
2. Write templates with your preferred tools.
3. Run `kapitan compile`.
4. Deploy the generated output from the `compiled/` directory.

### Supported input types

- [Jsonnet](https://kapitan.dev/pages/input_types/jsonnet/)
- [Jinja2](https://kapitan.dev/pages/input_types/jinja/)
- [Kadet (Python)](https://kapitan.dev/pages/input_types/kadet/)
- [Helm](https://kapitan.dev/pages/input_types/helm/)
- [Kustomize](https://kapitan.dev/pages/input_types/kustomize/)
- [CUE](https://kapitan.dev/pages/input_types/cuelang/)
- [External commands](https://kapitan.dev/pages/input_types/external/)
- [Copy / Remove](https://kapitan.dev/pages/input_types/copy/)

### Native integrations

- **Secret management**: GPG, HashiCorp Vault, AWS KMS, GCP KMS, Azure Key Vault
- **Remote dependencies**: Git, HTTP, ORAS (OCI registry)
- **Validation**: JSON Schema, TOML, YAML linting
- **GitOps-friendly**: compiles to fully rendered, plain-text output

## When to use Kapitan

- You manage the same application across many environments (dev, staging, prod, regions) and want a single source of truth.
- You need to reuse configuration fragments across targets without copy-paste.
- You want to combine multiple templating tools in one pipeline.
- You need native secret management embedded in the same configuration workflow.
- You prefer a compile step that generates fully rendered output before deployment.

## When another tool may be enough

- **Helm alone** is sufficient if you only need to template a single chart with values files and do not share complex configuration across many services.
- **Kustomize alone** is sufficient if your environment differences are mostly patches and overlays on a small set of bases.
- **Plain YAML with a CD tool** is sufficient if you have very few environments and simple configuration with little reuse.
- **Terraform alone** is sufficient if you only manage infrastructure resources and do not need a broader multi-language configuration layer.

## Project status

Kapitan is actively maintained by [KapiCorp](https://github.com/kapicorp) and the open source community. Releases are published regularly with [release notes](https://github.com/kapicorp/kapitan/releases). The project uses an [MIT license](LICENSE).

## Contributing

We welcome contributions. Please open an [issue](https://github.com/kapicorp/kapitan/issues) or [pull request](https://github.com/kapicorp/kapitan/pulls) to get started.

## Security

If you discover a security issue, please open a [private security advisory](https://github.com/kapicorp/kapitan/security/advisories/new) or contact the maintainers directly.

## Support

- Ask questions in the [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3) Slack channel.
- Read the [FAQ](https://kapitan.dev/FAQ/).
- Open a [GitHub Discussion](https://github.com/kapicorp/kapitan/discussions) or [Issue](https://github.com/kapicorp/kapitan/issues).

## Related projects

- [Tesoro](https://github.com/kapicorp/tesoro) — Kubernetes admission controller for Kapitan secrets.
- [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) — working examples to get started.
- [Kapitan Generators](https://generators.kapitan.dev) — reusable generators for common patterns.
