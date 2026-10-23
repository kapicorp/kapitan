---
title: "Kapitan FluxCD Integration: GitOps with OCI Artifacts"
description: "Integrate Kapitan with FluxCD to publish compiled manifests as OCI artifacts for GitOps delivery."
---

# :kapitan-logo: FluxCD Integration

Kapitan works with [FluxCD](https://fluxcd.io) by compiling manifests in CI and publishing them as [OCI artifacts](https://fluxcd.io/flux/cheatsheets/oci-artifacts/). FluxCD pulls the artifact and applies it to the cluster.

## Prerequisites

- FluxCD v2.0+
- `flux` CLI installed in your CI pipeline

## Workflow

1. CI runs `kapitan compile`
2. CI pushes the `compiled/` directory as an OCI artifact
3. FluxCD pulls the artifact and applies it

## CI

Push the compiled output with the `flux` CLI:

```shell
kapitan compile
flux push artifact oci://ghcr.io/org/app-manifests:$(git rev-parse --short HEAD) \
  --path="./compiled" \
  --source="$(git config --get remote.origin.url)" \
  --revision="$(git branch --show-current)@sha1:$(git rev-parse HEAD)"
```

## FluxCD Resources

Pull the artifact:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: app-manifests
  namespace: flux-system
spec:
  interval: 5m
  url: oci://ghcr.io/org/app-manifests
  ref:
    tag: latest
```

Apply it:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: OCIRepository
    name: app-manifests
  path: ./
  prune: true
  wait: true
```

See the [FluxCD OCI cheatsheet](https://fluxcd.io/flux/cheatsheets/oci-artifacts/) for tagging strategies, cosign signing, and verification.
