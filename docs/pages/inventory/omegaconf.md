# The Omegaconf inventory backend

## Overview

With version `0.33.0` we are introducing a new inventory backend as an alternative to reclass.

!!! warning

    OmegaConf is currently in experimental mode. If you encounter unexpected errors or bugs, please let us know and create an [issue](https://github.com/kapicorp/kapitan/issues/new/choose).


## Installation

The `omegaconf` Python package is an optional dependency of Kapitan.
You can install it as follows:

```shell
pip install kapitan[omegaconf]
```

## Usage

To use the omegaconf inventory backend, you need to pass `--inventory-backend=omegaconf` on the command line.
If you want to permanently switch to the omegaconf inventory backend, you can select the inventory backend in the [.kapitan config file](../commands/kapitan_dotfile.md):

```yaml
global:
  inventory-backend: omegaconf
```

## Differences to reclass

Here are all of the differences to using reclass, new features and some instructions, how to migrate your inventory.

### Supported:
* compose-node-name
* key overwrite prefix '`~`'
* interpolations
* relative class names
* init class
* nested interpolations
* escaped interpolations

### Not (yet) supported
* exports
* inventory queries
* interpolation to yaml-keys containing '`.`' (the delimiter itself)

### Syntax changes

OmegaConf uses the default yaml-path notation using dots (`.`) as key delimiter.

## New Functionalities

All of [OmegaConfs native functionalities](https://omegaconf.readthedocs.io/en/2.3_branch/grammar.html#the-omegaconf-grammar) are supported.

### General
* relative interpolation
* list accessing
* mandatory values
* Resolvers and Custom Resolvers

### Resolvers

Resolvers are the main benefits of using OmegaConf.
You can define any behavior with a python function that gets executed with the given input parameters.

We provide some basic resolvers:

* OmegaConf
  * `oc.env`: access a environment variable
  * `oc.select`: provide a default value for an interpolation
  * `oc.dict.keys`: get the keys of a dictionary object as a list
  * `oc.dict.values`: get the values of dictionary object as a list
* Utilities
  * `key`: get the name of the nodes key
  * `fullkey`: get the full name of the key
  * `parentkey`: get the name of the nodes parent key
  * `relpath`: takes an absolute path and convert it to relative
  * `tag`: creates an escaped interpolation
* Casting and Merging
  * `dict`: cast a dict inside a list into the actual dict
  * `list`: put a dict inside a list with that dict
  * `merge`: merge objects

### Usage

Using a resolver is as simple as an interpolation: `yamlkey: ${resolver:input}`

### Custom Resolver

You can write your own resolvers and are able to achieve any behavior you want.

In your inventory you have to create a file `resolvers.py`.
You should define a function `pass_resolvers()` that returns a dictionary with the resolvers name and the respective function pointer.

Now you can start writing Python functions with your custom resolvers.

### Example

```python
# inventory/resolvers.py

def concat(input1, input2):
    return input1 + input2

def add_ten(input):
    assert isinstance(input, int)
    return input + 10

def default_value():
    return "DEFAULT"

def split_dots(input: str):
    return input.split(".")

# required function
def pass_resolvers():
    return {"concat": concat, "plus_ten": add_ten, "default": default_value, "split", split_dots}
```

If we render a file the result would be:

```yaml
string: ${concat:Hello, World} # --> Hello World
int: ${plus_ten:90} # --> 100
default: ${default:} # --> DEFAULT
list: ${split:hello.world} # --> yaml list [hello, world]
```

## Access the feature

To access the feature you have to use a kapitan version >=0.33.0.

If this is your first time running you have to specify `--migrate` to adapt to OmegaConfs syntax.

!!! danger

    Please backup your inventory, if you're running `--migrate` or make sure you are able to revert the changes using source control.
    Also check your inventory if it contains some yaml errors like duplicate keys or wrong yaml types. The command will not change anything if some errors occur.

The migration consists of the following steps:
* replacing the delimiter '`:`' with '`.`' in interpolations
* replacing meta interpolations '`_reclass_`' to '`_kapitan_`'
* replacing escaped interpolations `\${content}` to resolver `${tag:content}`

## Examples

One important usecase with this is the definition of default values and overwriting them with specific target/component values.


```yaml
# inventory/classes/templates/deployment.yml
parameters:

  # define default values using the 'relpath' resolver
  deployment:

    namespace: ${target_name}
    component_name: \${parentkey:} # hack to get the components name

    labels:
      app.kubernetes.io/name: ${relpath:deployment.namespace} # gets resolved relatively

    image: ??? # OmegaConf mandatory value (has to be set in target)
    pull_policy: Always
    image_pull_secrets:
      - name: default-secret

    service_port: 8080 # default value

    service:
      type: ClusterIP
      selector:
        app: ${target_name}
    ports:
      http:
        service_port: ${relpath:deployment.service_port} # allows us to overwrite this in another key

```

```yaml
# inventory/targets/example.yml
classes:
  - templates.deployment

parameters:

  target_name: ${_kapitan_.name.short}

  components:
    # merge each component with a deployment
    backend: ${merge:${deployment}, ${backend}}
    keycloak: ${merge:${deployment}, ${keycloak}}
    keycloak-copy: ${merge:${keycloak}, ${keycloak-copy}} # merge with another component to specify even more

  # components config (would be in their own classes)

  # backend config
  backend:
    image: backend:latest

  # keycloak config
  keycloak:
    namespace: example1
    image: keycloak:latest

    env:
      [...]

  # keycloak-copy config (inherits env and namespace from keycloak)
  keycloak-copy:
    namespace: example2
```

This would generate the following components definition:

```yaml
components:
  backend:
    component_name: deployment
    image: backend:latest
    image_pull_secrets:
      - name: default-secret
    labels:
      app.kubernetes.io/name: example
    namespace: example
    ports:
      http:
        service_port: 8080
    pull_policy: Always
    service:
      selector:
        app: example
      type: ClusterIP
    service_port: 8080

  keycloak:
    component_name: deployment
    image: keycloak:latest
    image_pull_secrets:
      - name: default-secret
    labels:
      app.kubernetes.io/name: example1
    namespace: example1
    ports:
      http:
        service_port: 8080
    pull_policy: Always
    service:
      selector:
        app: example
      type: ClusterIP
    service_port: 8080

  keycloak-copy:
    component_name: deployment
    image: keycloak:latest
    image_pull_secrets:
      - name: default-secret
    labels:
      app.kubernetes.io/name: example1
    namespace: example2
    ports:
      http:
        service_port: 8080
    pull_policy: Always
    service:
      selector:
        app: example
      type: ClusterIP
    service_port: 8080
```
