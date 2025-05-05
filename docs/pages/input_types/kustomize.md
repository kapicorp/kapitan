# Kustomize Input Type

The Kustomize input type allows you to use [Kustomize](https://kustomize.io/) to manage and customize Kubernetes manifests within Kapitan. This input type is particularly useful when you need to:

- Apply patches to existing Kubernetes manifests
- Set namespaces for resources
- Manage multiple environments with overlays
- Customize resources without modifying the original manifests

## Configuration

The Kustomize input type supports the following configuration options:

```yaml
kapitan:
  compile:
    - output_path: manifests
      input_type: kustomize
      input_paths:
        - path/to/kustomize/overlay
      namespace: my-namespace  # Optional: Set namespace for all resources
      patches:  # Optional: Apply patches to resources
        patch-name:
          target:
            kind: Deployment
            name: my-deployment
            namespace: my-namespace
          patch:
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: my-deployment
              namespace: my-namespace
            spec:
              template:
                spec:
                  containers:
                    - name: my-container
                      image: nginx:1.19
```

### Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `output_path` | string | Path where compiled manifests will be written |
| `input_type` | string | Must be set to `kustomize` |
| `input_paths` | list | List of paths to Kustomize overlays |
| `namespace` | string | Optional: Namespace to set for all resources |
| `patches` | object | Optional: Dictionary of patches to apply |

## Examples

### Basic Usage

Here's a simple example that uses Kustomize to manage a deployment:

```yaml
# inventory/targets/my-app.yml
classes:
  - common

parameters:
  target_name: my-app
  kapitan:
    compile:
      - output_path: manifests
        input_type: kustomize
        input_paths:
          - kubernetes/base
        namespace: my-app
```

With the following directory structure:
```
kubernetes/
  base/
    kustomization.yaml
    deployment.yaml
```

```yaml
# kubernetes/base/kustomization.yaml
resources:
  - deployment.yaml
```

```yaml
# kubernetes/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
        - name: my-app
          image: nginx:latest
```

### Using Patches

Here's an example that uses patches to customize a deployment:

```yaml
# inventory/targets/my-app.yml
classes:
  - common

parameters:
  target_name: my-app
  kapitan:
    compile:
      - output_path: manifests
        input_type: kustomize
        input_paths:
          - kubernetes/base
        namespace: my-app
        patches:
          update-image:
            target:
              kind: Deployment
              name: my-app
              namespace: my-app
            patch:
              apiVersion: apps/v1
              kind: Deployment
              metadata:
                name: my-app
                namespace: my-app
              spec:
                template:
                  spec:
                    containers:
                      - name: my-app
                        image: nginx:1.19
```

### Multiple Environments

You can use Kustomize overlays to manage different environments:

```yaml
# inventory/targets/my-app-prod.yml
classes:
  - common

parameters:
  target_name: my-app-prod
  kapitan:
    compile:
      - output_path: manifests
        input_type: kustomize
        input_paths:
          - kubernetes/overlays/prod
        namespace: my-app-prod
```

With the following directory structure:
```
kubernetes/
  base/
    kustomization.yaml
    deployment.yaml
  overlays/
    prod/
      kustomization.yaml
      patches/
        replicas.yaml
```

```yaml
# kubernetes/overlays/prod/kustomization.yaml
resources:
  - ../../base
patches:
  - path: patches/replicas.yaml
```

```yaml
# kubernetes/overlays/prod/patches/replicas.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
```

## Best Practices

1. **Use Base and Overlays**: Organize your Kustomize resources using base and overlays for better maintainability.

2. **Keep Patches Small**: Create small, focused patches that modify specific aspects of resources.

3. **Use Namespaces**: Always specify namespaces in your patches to avoid conflicts.

4. **Version Control**: Keep your Kustomize resources in version control for better tracking and collaboration.

5. **Documentation**: Document your Kustomize overlays and patches for better maintainability.

## Troubleshooting

### Common Issues

1. **Patch Not Applied**: Ensure that the target resource exists and the patch format is correct.

2. **Namespace Issues**: Make sure to specify the namespace in both the target and patch.

3. **Resource Not Found**: Verify that the input paths are correct and the resources exist.

### Debugging

To debug Kustomize issues:

1. Check the generated kustomization.yaml in the temporary directory
2. Verify that all paths are correct
3. Ensure that patches are properly formatted
4. Check that target resources exist

## Related

- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/home/)
- [Kapitan Input Types](../input_types/introduction.md)
