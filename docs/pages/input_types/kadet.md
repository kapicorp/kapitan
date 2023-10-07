# :kapitan-logo: **Input Type | Kadet**

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

*Supported output types:*

- `yaml` (default)
- `json`
