---
tags:
  - kubernetes
---
# :kapitan-logo: **Kubernetes examples**

!!! danger
    This documentation is not up-to-date.

    Please refer to the [documentation](/pages/kapitan_overview/), [Getting started](/getting_started/) or look at the [Kapitan Reference](https://github.com/kapicorp/kapitan-reference) repository.

Here, we walk through how kapitan could be used to help create kubernetes manifests, whose values are customized for each target according to the inventory structure. The example folder can be found in our repository on Github at <https://github.com/kapicorp/kapitan/tree/master/examples/kubernetes>.

## Directory structure

The following tree shows what this directory looks like (only showing tree level 1):

```text
├── components
├── docs
├── inventory
├── lib
├── scripts
├── refs
└── templates
```

We will describe the role of each folder in the following sections.

### inventory

This folder contains the inventory values used to render the templates for each target. The structure of this folder is as follows:

```text
.
├── classes
│   ├── cluster
│   │   ├── common.yml
│   │   └── minikube.yml
│   ├── common.yml
│   └── component
│       ├── elasticsearch.yml
│       ├── mysql.yml
│       ├── namespace.yml
│       └── nginx.yml
└── targets
    ├── minikube-es.yml
    ├── minikube-mysql.yml
    └── minikube-nginx.yml

```

The required sub-folder is `targets`: during compile, kapitan searches for the yaml files under `targets` in order to identify the targets. In this example, there are three targets:

- minikube-es
- minikube-mysql
- minikube-nginx

 Therefore, when you run `kapitan compile`, under the `compiled` folder that kapitan generates, you will see three folders named after these targets.

`classes` is a folder that contains yaml files used as the "base class" in the hierarchical inventory database. The values defined here are inherited by the target files. For more explanation on how this works, look at the [inventory documentation](/inventory.md). Notice how the classes are nicely divided up into components and clusters, such as nginx and mysql, in order to clearly define what components each target should contain and to make the classes reusable.

For example, take a look at `targets/nginx.yml`:

```yaml
classes:
  - common
  - cluster.minikube
  - component.namespace
  - component.nginx

parameters:
  target_name: minikube-nginx
  namespace: ${target_name}
```

This target inherits values from four files under `classes` folder:

- common.yml
- cluster/minikube.yml
- component/namespace.yml
- component/nginx.yml

*Note: that some of these classes themselves may inherit from other classes.*

And the way classes are defined makes it easy to identify what components and clusters this target should contain and belong to!

Let's take a close look now at `component/namespace.yml`:

```yaml
parameters:
  namespace: ${target_name}
  kapitan:
    compile:
    - output_path: pre-deploy
      input_type: jsonnet
      output_type: yaml
      input_paths:
        - components/namespace/main.jsonnet
```

As we see, this file declares a `kapitan.compile` item whose input path (i.e. the template file) is `components/namespace/main.jsonnet` which, when rendered, will generate yaml file(s) under `compiled/minikube-nginx/pre-deploy`.

Don't confuse the `components` folder with `inventory/classes/components` folder: the former contains the actual templates, while the latter contains inventory classes.

### components

This folder contains the template files as discussed above, typically jsonnet and kadet files. The tree of this directory looks as follows:

```text
.
├── elasticsearch
│   ├── elasticsearch.container.jsonnet
│   ├── elasticsearch.statefulset.jsonnet
│   └── main.jsonnet
├── mysql
│   ├── main.jsonnet
│   ├── secret.jsonnet
│   ├── service.jsonnet
│   └── statefulset.jsonnet
├── namespace
│   └── main.jsonnet
└── nginx
    └── __init__.py
```

Notice how the directory structure corresponds to that of `inventory/classes/components` in order to make it easy to identify which templates are used for which components.

As mentioned above, we know that the target **minikube-nginx** inherits from `component.namespace`. Let's take a look at `components/namespace/main.jsonnet`:

```json
local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();
local p = inventory.parameters;

{
    "00_namespace": kube.Namespace(p.namespace),
    "10_serviceaccount": kube.ServiceAccount("default")
}
```

The first two lines import libjsonnet files under `lib` folder: this is the folder that contains helper files used inside templates. For example, `kapitan.libjsonnet` allows you to access inventory values inside jsonnet templates, and `kube.libjsonnet` defines functions to generate popular kubernetes manifests.

The actual object defined in `components/namespace/main.jsonnet` looks like this:

```json
{
    "00_namespace": kube.Namespace(p.namespace),
    "10_serviceaccount": kube.ServiceAccount("default")
}
```

We have "00_namespace" and "10_serviceaccount" as the keys. These will become files under `compiled/minikube-nginx/pre-deploy`, since `pre-deploy` is the `input_paths` declared in the inventory. For instance, `00_namespace.yml` would look like this:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  annotations: {}
  labels:
    name: minikube-nginx
  name: minikube-nginx
  namespace: minikube-nginx
spec: {}
```

### templates, docs, scripts

These folders contain jinja2 template files. For example, `component.elasticsearch` contains:

```yaml
kapitan:
  compile:
  # other items abbreviated for clarity
  - output_path: scripts
    input_type: jinja2
    input_paths:
      - scripts
  - output_path: .
    input_type: jinja2
    input_paths:
      - docs/elasticsearch/README.md
```

Since `component.elasticsearch` is inherited by the target **minikube-es**, this generates files under `compiled/minikube-es/scripts` and `compiled/minikube-es/README.md`.

### References

This folder contains references created manually by the user, or automatically by kapitan. Refer to [references management](/references.md) for how it works.

In this example, the configuration, such as the recipients, is declared in `inventory/classes/common.yml`:

```yaml
parameters:
  kapitan:
    vars:
      target: ${target_name}
      namespace: ${target_name}
    secrets:
      gpg:
        recipients:
          - name: example@kapitan.dev
            fingerprint: D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C
```

The references to the secrets are declared in `inventory/classes/component/mysql`, which is inherited by the target **minikube-mysql**. After running `kapitan compile`, some of the generated manifests contain the references to secrets. For example, have a look at `compiled/minikube-mysql/manifests/mysql_secret.yml`:

```yaml
apiVersion: v1
data:
  MYSQL_ROOT_PASSWORD: ?{gpg:targets/minikube-mysql/mysql/password:ec3d54de}
  MYSQL_ROOT_PASSWORD_SHA256: ?{gpg:targets/minikube-mysql/mysql/password_sha256:122d2732}
kind: Secret
metadata:
  annotations: {}
  labels:
    name: example-mysql
  name: example-mysql
  namespace: minikube-mysql
type: Opaque
```

`MYSQL_ROOT_PASSWORD` refers to the secret stored in `refs/targets/minikube-mysql/mysql/password` and so on.

You may reveal the secrets by running `kapitan refs --reveal -f mysql_secret.yml` and use the manifest by piping the output to kubectl!
