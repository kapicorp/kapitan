---
title: "Kubernetes Configuration Management with Kapitan"
description: "Learn how Kapitan helps you manage Kubernetes manifests across environments. Compare plain YAML, Helm, Kustomize, and Kapitan workflows with a practical example."
---

# :kapitan-logo: **Kubernetes Configuration Management with Kapitan**

Managing Kubernetes YAML across development, staging, and production is one of the most common reasons teams adopt Kapitan. This page explains how Kapitan helps you generate, organize, and validate Kubernetes configuration while avoiding duplication and drift.

## The problem

As your infrastructure grows, you typically face one or more of these issues:

- **Duplication:** the same `namespace`, `replicas`, or `image` is copy-pasted across dozens of files.
- **Drift:** a value changes in one place but not in another, causing environment inconsistencies.
- **Secrets sprawl:** sensitive values are hardcoded in YAML, scattered across repositories, or managed with ad-hoc scripts.
- **Tool fragmentation:** Helm values, Kustomize overlays, Terraform variables, and documentation all contain overlapping data that is never in sync.

Kapitan addresses these problems with an [inventory-driven model](inventory/introduction.md): you define data once in reusable [classes](inventory/classes.md), assign them to [targets](inventory/targets.md) (environments or services), and let Kapitan compile that data into the files each tool expects.

## How Kapitan manages Kubernetes configuration

Kapitan does not replace Kubernetes, kubectl, or your cluster. It is a pre-deployment configuration generator. The workflow looks like this:

1. **Model your data** in the Kapitan inventory (`inventory/classes/` and `inventory/targets/`).
2. **Choose an input type** for generating manifests: [Jsonnet](input_types/jsonnet.md), [Jinja](input_types/jinja.md), [Kadet](input_types/kadet.md), [Helm](input_types/helm.md), or [Kustomize](input_types/kustomize.md).
3. **Run `kapitan compile`** to render the final YAML or JSON files into `compiled/<target-name>/`.
4. **Apply the output** to your cluster with `kubectl apply -f compiled/<target-name>/manifests/` or via a GitOps pipeline.

Because the inventory is plain YAML, it is easy to read, diff, and review in pull requests. Because compilation is deterministic, you can validate the output before it ever reaches a cluster.

## Example: deploying an nginx service across environments

### Without Kapitan

You might have:

```
helm/values-dev.yaml
helm/values-staging.yaml
helm/values-prod.yaml
kustomize/overlays/dev/patch.yaml
kustomize/overlays/staging/patch.yaml
kustomize/overlays/prod/patch.yaml
terraform/variables.tf
```

Every time you change the `image` tag or `replicas` count, you must update multiple files. If you forget one, environments drift.

### With Kapitan

You define the common data once:

```yaml
# inventory/classes/components/nginx.yml
parameters:
  nginx:
    image: nginx:1.25
    replicas: 2
    ports:
      - 80
```

You override per environment:

```yaml
# inventory/classes/environments/production.yml
parameters:
  nginx:
    replicas: 5
```

You define the target:

```yaml
# inventory/targets/production/web.yml
classes:
  - components.nginx
  - environments.production

parameters:
  kapitan:
    compile:
      - output_path: manifests
        input_type: jinja2
        input_paths:
          - templates/nginx-deployment.yml.j2
```

The Jinja template can use the inventory directly:

```yaml
# templates/nginx-deployment.yml.j2
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: {{ inventory.parameters.target_name }}
spec:
  replicas: {{ inventory.parameters.nginx.replicas }}
  template:
    spec:
      containers:
        - name: nginx
          image: {{ inventory.parameters.nginx.image }}
          ports:
            {% for port in inventory.parameters.nginx.ports %}
            - containerPort: {{ port }}
            {% endfor %}
```

Running `kapitan compile -t production.web` produces:

```
compiled/production/web/manifests/nginx-deployment.yml
```

The `replicas` value is `5` because the production class overrides the component default. The `image` value is inherited from the component class. There is no duplication, and the entire configuration state is visible in one PR.

## Choosing an input type for Kubernetes

| Input type | Best for | Kubernetes workflow |
|---|---|---|
| [Jsonnet](input_types/jsonnet.md) | Structured manifests, libraries, validation | Write reusable Jsonnet libraries that output Deployment, Service, and ConfigMap objects |
| [Jinja](input_types/jinja.md) | Simple templates, documentation, scripts | Write plain YAML templates with loops and conditionals |
| [Kadet](input_types/kadet.md) | Python-based generation, complex logic | Build Kubernetes resources as Python classes and reuse them across components |
| [Helm](input_types/helm.md) | Existing Helm charts | Render upstream charts with values driven from the Kapitan inventory |
| [Kustomize](input_types/kustomize.md) | Patching base manifests | Apply environment-specific patches to manifests generated by another input type |

Many teams use more than one input type in the same project. For example, you might generate base manifests with Kadet and then patch them with Kustomize for environment-specific labels.

## Secrets in Kubernetes manifests

Kapitan's [References](../references.md) let you embed secrets in manifests without exposing plaintext values in the repository.

```yaml
parameters:
  mysql:
    root_password: ?{gpg:targets/${target_name}/mysql/root_password}
```

At compile time, the reference tag is embedded in the manifest. You can reveal it later with `kapitan refs --reveal` or use a tool like [Tesoro](https://github.com/kapicorp/tesoro) to decrypt it inside the cluster.

## Validation

You can validate generated manifests before applying them:

- Use the [`kapitan validate`](commands/kapitan_validate.md) command with JSON Schema.
- Use the `jsonschema()` function in [Jsonnet](input_types/jsonnet.md) to validate inventory structures at compile time.
- Pipe compiled output to `kubeval` or `kubectl apply --dry-run=client` in CI.

## GitOps integration

Kapitan fits naturally into GitOps workflows:

1. Engineers change inventory classes or templates in a pull request.
2. CI runs `kapitan compile` and validates the output.
3. The compiled directory is committed (or rendered on-the-fly by the CD pipeline).
4. ArgoCD, Flux, or a custom controller applies the compiled manifests to the cluster.

Because the inventory is declarative YAML, changes are easy to review. Because compilation is reproducible, the CD pipeline can trust the output.

---

## Next steps

- Learn how [Kapitan inventory](inventory/introduction.md) works with [targets](inventory/targets.md) and [classes](inventory/classes.md).
- Explore the [Kapitan vs Helm vs Kustomize](kapitan_vs_helm_kustomize.md) comparison.
- Try the [Kapitan examples](kapitan_examples.md) or clone the [kapitan-reference](https://github.com/kapicorp/kapitan-reference) repository.
- Set up [References](../references.md) for managing secrets in your Kubernetes configuration.
