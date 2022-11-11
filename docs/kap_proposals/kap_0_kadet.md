# Kadet

This introduces a new experimental input type called Kadet.

Kadet is essentially a Python module offering a set of classes and functions to define objects which will compile to JSON or YAML. A complete example is available in `examples/kubernetes/components/nginx`.

Author: @ramaro

## Overview

### BaseObj

BaseObj implements the basic object implementation that compiles into JSON or YAML.
Setting keys in `self.root` means they will be in the compiled output. Keys can be set as an hierarchy of attributes (courtesy of [addict](https://github.com/mewwts/addict))
The `self.body()` method is reserved for setting self.root on instantiation:

The example below:

```python
class MyApp(BaseObj):
 def body(self):
   self.root.name = "myapp"
   self.root.inner.foo = "bar"
   self.root.list = [1, 2, 3]
```

compiles into:

```yaml
---
name: myapp
inner:
  foo: bar
list:
  - 1
  - 2
  - 3
```

The `self.new()` method can be used to define a basic constructor.
`self.need()` checks if a key is set and errors if it isn't (with an optional custom error message).
`kwargs` that are passed onto a new instance of BaseObj are always accessible via `self.kwargs`
In this example, MyApp needs `name` and `foo` to be passed as kwargs.

```python
class MyApp(BaseObj):
 def new(self):
   self.need("name")
   self.need("foo", msg="please provide a value for foo")

 def body(self):
   self.root.name = self.kwargs.name
   self.root.inner.foo = self.kwargs.foo
   self.root.list = [1, 2, 3]

obj = MyApp(name="myapp", foo="bar")
```

### Setting a skeleton

Defining a large body with Python can be quite hard and repetitive to read and write.
The `self.update_root()` method allows importing a YAML/JSON file to set the skeleton of self.root.

MyApp's skeleton can be set instead like this:

```yaml
#skel.yml
---
name: myapp
inner:
  foo: bar
list:
  - 1
  - 2
  - 3
```

```python
class MyApp(BaseObj):
 def new(self):
   self.need("name")
   self.need("foo", msg="please provide a value for foo")
   self.update_root("path/to/skel.yml")
```

Extending a skeleton'd MyApp is possible just by implementing `self.body()`:

```python
class MyApp(BaseObj):
 def new(self):
   self.need("name")
   self.need("foo", msg="please provide a value for foo")
   self.update_root("path/to/skel.yml")

 def body(self):
   self.set_replicas()
   self.root.metadata.labels = {"app": "mylabel"}

def set_replicas(self):
   self.root.spec.replicas = 5
```

#### Inheritance

Python inheritance will work as expected:

```python

class MyOtherApp(MyApp):
  def new(self):
    super().new()  # MyApp's new()
    self.need("size")

def body(self):
   super().body()  #  we want to extend MyApp's body
   self.root.size = self.kwargs.size
   del self.root.list  # get rid of "list"

obj = MyOtherApp(name="otherapp1", foo="bar2", size=3)
```

compiles to:

```yaml
---
name: otherapp1
inner:
  foo: bar2
replicas: 5
size: 3
```

## Components

A component in Kadet is a python module that must implement a `main()` function returning an instance of`BaseObj`. The inventory is also available via the `inventory()` function.

For example, a `tinyapp` component:

```python
# components/tinyapp/__init__.py
from kapitan.inputs.kadet import BaseOBj, inventory
inv = inventory() # returns inventory for target being compiled

class TinyApp(BaseObj):
  def body(self):
    self.root.foo = "bar"
    self.root.replicas = inv.parameters.tinyapp.replicas

def main():
  obj = BaseOb()
  obj.root.deployment = TinyApp() # will compile into deployment.yml
  return obj
```

An inventory class must be created for `tinyapp`:

```yaml
# inventory/classes/components/tinyapp.yml

parameters:
  tinyapp:
    replicas: 1
  kapitan:
    compile:
    - output_path: manifests
      input_type: kadet
      output_type: yaml
      input_paths:
        - components/tinyapp
```

### Common components

A library in `--search-paths` (which now defaults to `.` and `lib/`) can also be a module that kadet components import. It is loaded using the `load_from_search_paths()`:

```python
kubelib = load_from_search_paths("kubelib") # lib/kubelib/__init__.py

def main():
  obj = BaseObj()
  obj.root.example_app_deployment = kubelib.Deployment(name="example-app")
  return obj
```
