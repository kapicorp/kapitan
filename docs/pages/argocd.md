# :kapitan-logo: ArgoCD Integration

Kapitan can be used as an [ArgoCD Config Management Plugin (CMP)](https://argo-cd.readthedocs.io/en/stable/operator-manual/config-management-plugins/).

## Prerequisites

- ArgoCD v2.8+
- The `kapicorp/kapitan` image accessible from your cluster

## Setup

Add a Kapitan sidecar to the ArgoCD repo-server. The sidecar must:

- Run the `kapicorp/kapitan` image
- Start with `/var/run/argocd/argocd-cmp-server` (copied from the ArgoCD image via an init container)
- Mount a CMP plugin config that defines a `generate` command for Kapitan

### CMP plugin config

The `generate` command should produce Kubernetes manifests from your compiled output. A typical script concatenates the generated YAML files and runs `kapitan refs --reveal` to decrypt secrets:

```bash
rm -rf all_manifests.yml
for f in *.yml; do
  echo '---' >> all_manifests.yml
  cat "$f" >> all_manifests.yml
done
kapitan refs --reveal --file all_manifests.yml
```

A minimal Helm values snippet:

```yaml
configs:
  cmp:
    plugins:
      kapitan:
        generate:
          command: [bash, -c]
          args:
            - |
              rm -rf all_manifests.yml
              for f in *.yml; do
                echo '---' >> all_manifests.yml
                cat "$f" >> all_manifests.yml
              done
              kapitan refs --reveal --file all_manifests.yml

repoServer:
  extraContainers:
    - name: kapitan
      image: kapicorp/kapitan
      command: [/var/run/argocd/argocd-cmp-server]
      volumeMounts:
        - mountPath: /var/run/argocd
          name: var-files
        - mountPath: /home/argocd/cmp-server/plugins
          name: plugins
        - mountPath: /home/argocd/cmp-server/config/plugin.yaml
          name: cmp-plugin
          subPath: plugin.yaml
```

See the [ArgoCD CMP documentation](https://argo-cd.readthedocs.io/en/stable/operator-manual/config-management-plugins/) for the full sidecar wiring.

## Application

Create an ArgoCD Application that uses the plugin:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-kapitan-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/example/kapitan-project.git
    targetRevision: main
    path: compiled/my-target
    plugin:
      name: kapitan
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

Update `spec.source.repoURL` and `spec.source.path` to match your repository and compiled target output.
