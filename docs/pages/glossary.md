---
title: "Kapitan Glossary: Key Terms & Concepts Explained"
description: "Definitions of key terms and concepts used throughout Kapitan documentation and the configuration management workflow."
---

# Glossary

This page defines the key terms used throughout Kapitan. Use it to quickly look up a concept or to understand how ideas relate to each other.

## Inventory terms

### Inventory

The hierarchical data store that feeds configuration into Kapitan. It is built from classes and targets stored as YAML files under the `inventory/` directory. The inventory is the single source of truth for all parameters that templates consume during compilation.

[Learn more about the inventory](inventory/introduction.md)

### Target

A specific environment or deployment unit that Kapitan compiles. Each target is a YAML file under `inventory/targets/` that lists classes to inherit and defines its own parameters. A target name is derived from its relative path: `inventory/targets/prod.yml` becomes `prod`, and `inventory/targets/teams/devops/grafana.yml` becomes `teams.devops.grafana`.

[Learn more about targets](inventory/targets.md)

### Class

A reusable YAML fragment under `inventory/classes/` that defines shared parameters and can reference other classes. Classes let you compose configuration without copy-paste. A class name is derived from its relative file path, with `init.yml` files mapping to their parent directory name (the reclass convention).

[Learn more about classes](inventory/classes.md)

### Parameters

The `parameters` section in a target or class file. This is where you define the key-value data that templates read during compilation. Parameters can be scalar values, lists, or nested dictionaries.

### Parameter interpolation

The mechanism that lets you reference other parameter values using `${...}` syntax. For example, `${teams.devops.config.region}` resolves to the value defined in another part of the inventory. Different backends support different interpolation features.

[Learn more about parameter interpolation](inventory/parameters_interpolation.md)

### Inventory backend

The engine that parses and merges the inventory. Kapitan supports multiple backends:

- **reclass** — the default Python backend.
- **reclass-rs** — a faster Rust implementation of reclass.
- **omegaconf** — an alternative backend with different merging and interpolation behavior.

[Learn more about backends](inventory/backends.md)

## Compilation terms

### Compile

The process of reading the inventory, running input templates, and writing generated files to the `compiled/` directory. You trigger compilation with `kapitan compile`. Each target gets its own subdirectory under `compiled/` that mirrors the target name.

[Learn more about compilation](core_concepts.md)

### Input type

The templating engine or data source that produces output during compilation. Kapitan supports many input types, including Jsonnet, Jinja2, Kadet (Python), Helm, Kustomize, CUE, external commands, copy, and remove. Each input type is configured inside the `kapitan.compile` list of a target.

[Learn more about input types](input_types/introduction.md)

### Compiled output

The directory tree produced by `kapitan compile`, located at `compiled/`. Each target has its own subdirectory containing the generated files. This output is plain text and can be committed to version control, reviewed in pull requests, or fed directly to a deployment pipeline.

### Parallelism

Kapitan compiles targets in parallel using multiple processes. The default parallelism is `min(number_of_targets, cpu_count)`. You can control it with the `-p` flag.

## References and secrets

### Reference

A placeholder for a value that is stored outside the inventory, typically because it is sensitive or highly variable. References use the syntax `?{backend:path}`. During compilation, Kapitan replaces the reference with the actual value. During reveal, encrypted references are decrypted.

[Learn more about references](../references.md)

### Refs directory

The directory where reference files are stored, defaulting to `refs/` in the repository root. Each backend stores its data in a different format within this directory.

### Reveal

The process of decrypting or resolving references so that plain-text values appear in the compiled output. Use `kapitan refs --reveal` to reveal references in existing files.

### Compile-time references

References that are resolved during `kapitan compile`. The compiled output contains the plain value. This requires the appropriate backend credentials or keys to be available at compile time.

## Dependencies

### External dependency

A remote resource that Kapitan fetches before compilation. Supported sources include Git repositories, HTTP(S) URLs, and ORAS (OCI registry) artifacts. Dependencies are declared in `kapitan.dependencies` inside a target.

[Learn more about external dependencies](external_dependencies.md)

### Generator

A reusable template or script that produces Kapitan-compatible output. Generators are often distributed as Git repositories and can be fetched as dependencies. The Kapitan Generators project hosts community generators.

[Learn more about generators](https://generators.kapitan.dev)

## Validation and tooling

### Validate

The process of checking generated output against schemas or rules. Kapitan supports JSON Schema validation, YAML linting, and TOML validation. Validation helps catch configuration errors before deployment.

### Searchvar

A Kapitan subcommand that searches the inventory for parameter values. It is useful for finding where a specific value is defined or used across targets.

### Lint

Static analysis of Kapitan configuration files. The `kapitan lint` command checks for common issues in inventory files, templates, and compiled output.

## GitOps and deployment

### GitOps

An operational model where the desired state of infrastructure is stored in Git and an automated process applies changes. Kapitan fits into GitOps workflows because it compiles plain-text, reviewable configuration that can be committed and deployed by a CD controller.

### Compiled manifest

A generated configuration file ready for deployment. In a Kubernetes context, this is typically a YAML manifest. In a Terraform context, this is a `.tf` file or a Terraform plan. Kapitan itself does not deploy; it generates the artifacts that a deployment tool consumes.

## See also

- [Core Concepts](core_concepts.md)
- [Inventory Introduction](inventory/introduction.md)
- [Input Types Introduction](input_types/introduction.md)
- [References](../references.md)
- [FAQ](../FAQ.md)
- [Support](../support.md)
