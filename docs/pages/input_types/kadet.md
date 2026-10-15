---
title: "Kapitan Kadet Input Type: Python Config Generation"
description: "Use Python and Kadet with Kapitan to generate infrastructure configuration. Define resources as classes and access the Kapitan inventory from Python code."
---

# :kapitan-logo: **Kapitan Kadet Input Type**

Kadet is an extensible **input type** for **Kapitan** that enables you to generate templates using **Python**.

The key benefit being the ability to utilize familiar programing principles while having access to **Kapitan**'s powerful inventory system.

A library that defines resources as classes using the Base Object class is required. These can then be utilized within components to render output.

The following functions are provided by the class `BaseObj()`.

Method definitions:

- `new()`: Provides parameter checking capabilities
- `body()`: Enables in-depth parameter configuration

Method functions:

- `root()`: Defines values that will be compiled into the output
- `need()`: Ability to check & define input parameters
- `update_root()`: Updates the template file associated with the class

A class can be a resource such as a **Kubernetes** Deployment as shown here:

```python
class Deployment(BaseObj): # (1)!
    def new(self): # (2)!
        self.need("name", "name string needed")
        self.need("labels", "labels dict needed")
        self.need("containers", "containers dict needed")
        self.update_root("lib/kubelib/deployment.yml")

    def body(self): # (3)!
        self.root.metadata.name = self.kwargs.name # (4)!
        self.root.metadata.namespace = inv.parameters.target_name
        self.root.spec.template.metadata.labels = self.kwargs.labels
        self.root.spec.template.spec.containers = self.kwargs.containers
```

1. The deployment is an `BaseObj()` which has two main functions.
2. `new(self)` is used to perform parameter validation & template compilation
3. `body(self)` is utilized to set those parameters to be rendered.
4. `self.root.metadata.name` is a direct reference to a key in the corresponding yaml.


**Kadet** supports importing libraries as you would normally do with Python. These libraries can then be used by the components to generate the required output.



```python
...
kubelib = kadet.load_from_search_paths("kubelib") #(1)!
...
name = "nginx"
labels = kadet.BaseObj.from_dict({"app": name})
nginx_container = kubelib.Container( #(2)!
    name=name, image=inv.parameters.nginx.image, ports=[{"containerPort": 80}]
)
...
def main():
    output = kadet.BaseObj() #(3)!
    output.root.nginx_deployment = kubelib.Deployment(name=name, labels=labels, containers=[nginx_container]) #(4)!
    output.root.nginx_service = kubelib.Service( #(5)!
        name=name, labels=labels, ports=[svc_port], selector=svc_selector
    )
    return output #(6)!
```

1. We import a library called `kubelib` using `load_from_search_paths()`
2. We use `kubelib` to create a `Container`
3. We create an output of type `BaseObj` and we will be updating the `root` element of this output.
4. We use `kubelib` to create a `Deployment` kind. The Deployment makes use of the Container created.
5. We use `kubelib` to create a `Service` kind.
6. We return the object. **Kapitan** will render everything under `output.root`

Kadet uses a library called [addict](https://github.com/mewwts/addict) to organise the parameters inline with the yaml templates.
As shown above we create a `BaseObject()` named output. We update the root of this output with the data structure returned from kubelib. This output is what is then returned to kapitan to be compiled into the desired output type.

For a deeper understanding please refer to [github.com/kapicorp/kadet](https://github.com/kapicorp/kadet)

## Writing a generator

A generator is a Kadet component that reads its settings from the inventory and returns the files to write. This section describes what Kapitan expects from it.

### Files

A generator is a directory with an `__init__.py` that defines `main()`. Kapitan loads `__init__.py` as a package, so helper modules in the same directory are imported relatively (`from .base import ...`). A kadet input path must be a directory; a path to a single `.py` file fails with `path: ... must be an existing directory`.

### Wiring a target

A kadet compile entry lists the generator directory in `input_paths`. Kapitan looks the path up in the search paths (`.` and `lib` by default, see `--search-paths`). A generator that is not part of the repository is fetched with a [dependency](../external_dependencies.md), for example from an OCI registry as described in [Publishing generators](../publishing_generators.md), and `kapitan compile --fetch` pulls it before compiling. The settings live in the inventory:

```yaml
parameters:
  kapitan:
    dependencies:
      - type: oci
        source: registry.example.com/generators/example:1.0.0
        output_path: lib/example
    compile:
      - input_type: kadet
        input_paths:
          - lib/example
        output_path: manifests
        input_params: {}
  generators:
    example:
      configmaps:
        settings:
          data:
            LOG_LEVEL: info
```

```python
# lib/example/__init__.py
from kapitan.inputs.kadet import BaseObj, inventory


def main(input_params):
    output = BaseObj()
    settings = inventory().parameters.generators.example
    for name, configmap in settings.configmaps.items():
        output.root[f"{name}-cm"] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": name},
            "data": configmap.data,
        }
    return output
```

This target compiles to `compiled/<target>/manifests/settings-cm.yaml`.

### What `main()` receives

For each path in `input_paths`, Kapitan imports the directory's `__init__.py` and calls `main(input_params)`, or `main()` when the function takes no positional parameter. A `main()` with two or more positional parameters fails the compile with `main parameters not equal to 1 or 0`.

`input_params` is a shallow copy of the entry's `input_params` as rendered by the inventory, plus `compile_path` unless the entry sets that key itself. Kapitan reads no other key, so none is required.

`compile_path` is the directory the entry writes to. During the compile it is a temporary directory, `<tmp>/compiled/<target>/<output_path>`, which Kapitan copies to `compiled/` after all targets have compiled.

### Reading the inventory

`kapitan.inputs.kadet` provides the inventory as `kadet.Dict` objects with attribute access:

- `inventory()` returns the current target's inventory, for example `inventory().parameters.generators.example`.
- `inventory_global()` returns the inventory of every target, keyed by target name.
- `topics(name)` returns the targets that publish a topic, see [Topics](../inventory/advanced.md#topics).

### What `main()` returns

`main()` returns a `BaseObj`, a `BaseModel` or a `dict`. Every top-level key, of `root` for a `BaseObj` or `BaseModel`, becomes one file below the entry's `output_path`, and a `/` in the key creates subdirectories. So one call can write many files, as with Jsonnet. A return value of `None` or an empty object writes nothing.

The entry's `output_type` sets the format and the extension that is appended to the key:

| `output_type` | File for key `settings-cm` |
|---|---|
| `yaml` (default) | `settings-cm.yaml` |
| `yml` | `settings-cm.yml` |
| `json` | `settings-cm.json` |
| `toml` | `settings-cm.toml` |
| `plain` | `settings-cm`, the value must be a string |
| `auto` | the key's own extension if it is `.yaml`, `.yml`, `.json` or `.toml`, otherwise YAML with `.yaml` appended |

With YAML output, a list value is written as a multi-document file with one document per item.

### Errors

- An exception raised in `main()` fails the target with `Could not load Kadet module: <directory>`, with the original exception chained as its cause.
- An exception while importing the module, for example in module-level code or a failing import, is not wrapped and fails the target with `Error compiling <target>: <message>`.
- A missing `main` or a return value without keys, such as a list, fails with `Invalid input_type: "kadet"` followed by the `AttributeError`.
- An input path that no search path contains fails with `<path> for target: <target> not found in search_paths`, unless the entry sets `ignore_missing: true`.

With `continue_on_compile_error: true` on the entry, Kapitan logs the error and continues with the next compile entry.
