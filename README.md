# Kapitan: tool to manage kubernetes configuration using jsonnet templates

[![Build Status](https://travis-ci.org/deepmind/kapitan.svg?branch=master)](https://travis-ci.org/deepmind/kapitan)

Kapitan is a command line tool for declaring, instrumenting and documenting
infrastructure with the goal of writing reusable components in Kubernetes whilst avoiding
duplication and promoting conventions and patterns for extensibility.

## Main Features

* Jsonnet data templating
* Targets
* Inventory
* Jinja2 jsonnet templating

## Getting Started

The instructions below will help you getting started with a copy of Kapitan on
your local machine so you can start using and developing it.

### Prerequisites

Kapitan needs Python 2.7+ and can be installed with pip.

```
$ pip install https://github.com/deepmind/kapitan.git@v0.9.14

```

# Usage

For the example below, compiling the minikube-es target in the
_examples_ directory

```
$ cd examples/
$ kapitan compile -f targets/minikube-es/target.json
Wrote compiled/minikube-es/manifests/es-master.yml
Wrote compiled/minikube-es/manifests/es-elasticsearch-svc.yml
Wrote compiled/minikube-es/manifests/es-discovery-svc.yml
Wrote compiled/minikube-es/manifests/es-client.yml
Wrote compiled/minikube-es/manifests/es-data.yml
Wrote compiled/minikube-es/scripts/setup.sh with mode 0740
Wrote compiled/minikube-es/scripts/kubectl.sh with mode 0740
Wrote compiled/minikube-es/docs/README.md with mode 0640
```

Compiled manifests will be available at:

```
compiled/minikube-es
```

An alternative output path can be set with ```--output-path=/path/for/compiled```

Example:

```
$ find compiled/
compiled/
compiled/minikube-es
compiled/minikube-es/scripts
compiled/minikube-es/scripts/kubectl.sh
compiled/minikube-es/scripts/setup.sh
compiled/minikube-es/docs
compiled/minikube-es/docs/README.md
compiled/minikube-es/manifests
compiled/minikube-es/manifests/es-client.yml
compiled/minikube-es/manifests/es-data.yml
compiled/minikube-es/manifests/es-master.yml
compiled/minikube-es/manifests/es-elasticsearch-svc.yml
compiled/minikube-es/manifests/es-discovery-svc.yml
```

All manifests can then be applied at once using kubectl:

```
$ kubectl --context=minikube apply --dry-run -f compiled/minikube-es/manifests/
```

Or using the compiled kubectl.sh which defaults to the example target:

```
$ compiled/minikube-es/scripts/kubectl.sh apply --dry-run -f compiled/minikube-es/manifests/
statefulset "cluster-client" configured (dry run)
statefulset "cluster-data" configured (dry run)
service "elasticsearch-discovery" configured (dry run)
service "elasticsearch" configured (dry run)
statefulset "cluster-master" configured (dry run)
```

Get this target's pods:

```
$ ./compiled/minikube-es/scripts/kubectl.sh get pods -w
NAME               READY     STATUS    RESTARTS   AGE
cluster-client-0   1/1       Running   0          50s
cluster-data-0     1/1       Running   0          20s
cluster-master-0   1/1       Running   0          59s
```

## Feature Overview

### Jsonnet data templating

Kapitan builds on top of the [Jsonnet](https://jsonnet.org) language, _a domain specific configuration language
that helps you define JSON data._

### Targets

Targets define what to compile with what parameters and where.

Kapitan requires a target file to compile a target and its parameters.

The target snippet below will compile the jsonnet file at _targets/minikube-es/main.jsonnet_ with target and namespace _minikube-es_.

```
{
    "version": 1,
    "vars": {
        "target": "minikube-es",
        "namespace": "minikube-es"
    },
    "compile": [
        {
            "name": "manifests",
            "type": "jsonnet",
            "path": "targets/minikube-es/main.jsonnet",
            "output": "yaml"
        }
    ]
}
```

The compiled files will be written in YAML format into the "manifests" directory:

```
$ find compiled/
compiled/
compiled/minikube-es
compiled/minikube-es/manifests
compiled/minikube-es/manifests/es-client.yml
compiled/minikube-es/manifests/es-data.yml
compiled/minikube-es/manifests/es-master.yml
compiled/minikube-es/manifests/es-elasticsearch-svc.yml
compiled/minikube-es/manifests/es-discovery-svc.yml
```

Other compile types can be specified, like _jinja2_:

```
{
    "version": 1,
    "vars": {
        "target": "minikube-es",
        "namespace": "minikube-es"
    },
    "compile": [
        {
            "name": "manifests",
            "type": "jsonnet",
            "path": "targets/minikube-es/main.jsonnet",
            "output": "yaml"
        },
        {
            "name": "docs",
            "type": "jinja2",
            "path": "targets/minikube-es/docs"
        }
    ]
}
```

Compiling this target will create directories _manifests_ and _docs_:

```
$ find compiled/
compiled/
compiled/minikube-es
compiled/minikube-es/docs
compiled/minikube-es/docs/README.md
compiled/minikube-es/manifests
compiled/minikube-es/manifests/es-client.yml
compiled/minikube-es/manifests/es-data.yml
compiled/minikube-es/manifests/es-master.yml
compiled/minikube-es/manifests/es-elasticsearch-svc.yml
compiled/minikube-es/manifests/es-discovery-svc.yml
```


### Inventory

The inventory allows you to define values in a hierarchical way. The current implementation uses [reclass](https://github.com/madduck/reclass), a library that provides a simple way to classify nodes (targets).

By default, Kapitan will look for an _inventory/_ directory to render the inventory from.

#### Inventory Classes

Classifying almost anything will help you avoid repetition (DRY) and will force you to organise parameters hierarchically.

For example, the snipppet below, taken from the example elasticsearch class, declares
what parameters are needed for the elasticsearch component:

```
$ cat inventory/classes/app/elasticsearch.yml
parameters:
  elasticsearch:
    image: "quay.io/pires/docker-elasticsearch-kubernetes:5.5.0"
    java_opts: "-Xms512m -Xmx512m"
    replicas: 1
    masters: 1
    roles:
      master:
        image: ${elasticsearch:image}
        java_opts: ${elasticsearch:java_opts}
        replicas: ${elasticsearch:replicas}
        masters: ${elasticsearch:masters}
      data:
        image: ${elasticsearch:image}
        java_opts: ${elasticsearch:java_opts}
        replicas: ${elasticsearch:replicas}
        masters: ${elasticsearch:masters}
...
```

#### Inventory Targets

The example inventory target _minikube-es_ includes the elasticsearch and minikube classes
as a way to say "I want the minikube-es target with the parameters defined in
the elasticsearch app and minikube cluster classes":

```
$ cat inventory/targets/minikube-es.yml
classes:
  - cluster.minikube
  - app.elasticsearch
```

#### Having a look

Rendering the inventory for the _minikube-es_ target:

```
$ kapitan inventory -t minikube-es
...
classes:
  - cluster.minikube
  - app.elasticsearch
environment: base
parameters:
  cluster:
    name: minikube
    user: minikube
  elasticsearch:
    image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
    java_opts: -Xms512m -Xmx512m
    masters: 1
    replicas: 1
    roles:
      client:
        image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
        java_opts: -Xms512m -Xmx512m
        masters: 1
        replicas: 1
      data:
        image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
        java_opts: -Xms512m -Xmx512m
        masters: 1
        replicas: 1
...
```


#### Inventory in jsonnet

Accessing the inventory from jsonnet compile types requires you to import "kapitan.libjsonnet" located in the jsonnet/ directory, which includes the native_callback functions glueing reclass to jsonnet (amongst others).

The jsonnet snippet below imports the inventory for the target you're compiling
and returns the java_opts for the elasticsearch data role:

```
local kap = import "lib/kapitan.libjsonnet";
inventory = kap.inventory();

{
    "data_java_opts": inventory.parameters.elasticsearch.roles.data.java_opts,
}
```

#### Inventory in jinja2

Jinja2 types will pass the "inventory" and whatever target vars as context keys in your template.

This snippet renders the same java_opts for the elasticsearch data role:

```
java_opts for elasticsearch data role are: {{ inventory.parameters.elasticsearch.roles.data.java_opts }}
```


### Jinja2 jsonnet templating

Such as reading the inventory within jsonnet, Kapitan also provides a function to render a Jinja2 template file. Again, importing "kapitan.jsonnet" is needed.

The jsonnet snippet renders the jinja2 template in templates/got.j2:

```
local kap = import "lib/kapitan.libjsonnet";

{
    "jon_snow": kap.jinja2_template("templates/got.j2", { is_dead: false }),
}
```

It's up to you to decide what the output is.
