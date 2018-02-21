# Kapitan: Generic templated configuration management for Kubernetes, Terraform and other things

[![Build Status](https://travis-ci.org/deepmind/kapitan.svg?branch=master)](https://travis-ci.org/deepmind/kapitan)

Kapitan is a tool to manage complex deployments using mixed templating frameworks.

Use your template of choice to manage your Kubernetes manifests, your documentation, your Terraform configuration or even simplify your scripts.

How is it different from [`Helm`](https://github.com/kubernetes/helm)? Please look at our [FAQ](#faq)!

<img src="https://raw.githubusercontent.com/deepmind/kapitan/master/docs/kapitan_logo.png" width="250">

# Table of Contents

* [Main Features](#main-features)
* [Installation](#installation)
* [Example](#example)
* [Main concepts](#main-concepts)
* [Typical folder structure](#typical-folder-structure)
* [Usage](#usage)
* [Modes of operation](#modes-of-operation)
* [Credits](#credits)
* [FAQ](#faq)
* [Related projects](#related-projects)



# Main Features

* Use [reclass](https://github.com/madduck/reclass) to build an inventory of data/variables for all your deployments as a whole, avoiding dangerous duplications, and improving readibility.
* Use [Jsonnet](https://github.com/google/jsonnet) to create json/yaml based configurations (e.g. Kubernetes, Terraform);
* Use [Jinja2](http://jinja.pocoo.org/docs/2.9/) to create text based templates for scripts and documentation;
* Manage secrets by defining who can see them, without compromising collaboration with other users.
* Create dynamically generated documentation about a single deployment (i.e. ad-hoc instructions) or all deployments at once (i.e. global state of deployments)



# Installation

Kapitan needs Python 2.7+ and can be installed with pip.

```
$ pip install git+https://github.com/deepmind/kapitan.git
```



# Example

The example below _compiles_ 3 targets inside the `examples/kubernetes` folder.
Each target represents a different namespace in a minikube cluster

These targets generate the following resources:

* Kubernetes `StatefulSet` for ElasticSearch Master node
* Kubernetes `StatefulSet` for ElasticSearch Client node
* Kubernetes `StatefulSet` for ElasticSearch Data node
* Kubernetes `Service` to expose ElasticSearch discovery port
* Kubernetes `Service` to expose ElasticSearch service port
* Kubernetes `StatefulSet` for mySQL
* Kubernetes `Service` to expose mySQL service port
* Kubernetes `Secret` for mySQL
* Script `setup.sh` to configure kubectl context for this target
* Script `kubectl.sh` to control this target
* Documentation

![demo](https://raw.githubusercontent.com/deepmind/kapitan/master/docs/demo.gif)

```
$ cd examples/kubernetes

$ kapitan compile
Compiled minikube-mysql
Compiled minikube-es
Compiled minikube-es-2
```



# Main concepts

### Targets

A target usually represents a single namespace in a kubernetes cluster and defines all components, scripts and documentation that will be generated for that target.

Kapitan requires a target file to compile a target and its parameters. Example:

```
$ cat examples/targets/minikube-es/target.yml
---
vars:
  target: minikube-es
  namespace: minikube-es
compile:

  - output_path: manifests
    input_type: jsonnet
    input_paths:
      - targets/minikube-es/main.jsonnet
    output_type: yaml

  - output_path: scripts
    input_type: jinja2
    input_paths:
      - scripts

  - output_path: .
    input_type: jinja2
    input_paths:
      - targets/minikube-es/docs/README.md
```

### Components

A component is an aplication that will be deployed to a kubernetes cluster. This includes all necessary kubernetes objects (StatefulSet, Services, ConfigMaps) defined in jsonnet.
It may also include scripts, config files and dynamically generated documentation defined using Jinja templates.


### Inventory

This is a hierarchical database of variables that are passed to the targets during compilation.

By default, Kapitan will look for an `inventory/` directory to render the inventory from.

There are 2 types of objects inside the inventory:


#### Inventory Classes

Classes define variables that are shared across many targets. You can have for example a `component.elasticsearch` class with all the default values for targets using elasticsearch. Or a `production` or `dev` class to enable / disable certain features based on the type of target.

You can always override values further up the tree (i.e. in the inventory target file or in a class that inherits another class)

Classifying almost anything will help you avoid repetition (DRY) and will force you to organise parameters hierarchically.

For example, the snipppet below, taken from the example elasticsearch class, declares
what parameters are needed for the elasticsearch component:

```
$ cat inventory/classes/component/elasticsearch.yml
parameters:
  elasticsearch:
    image: "quay.io/pires/docker-elasticsearch-kubernetes:5.5.0"
    java_opts: "-Xms512m -Xmx512m"
    replicas: 1
    roles:
      master:
        image: ${elasticsearch:image}
        java_opts: ${elasticsearch:java_opts}
        replicas: ${elasticsearch:replicas}
...
```

#### Inventory Targets

Inside the inventory target files you can include classes and define new values or override any values inherited from the included classes.
For example:

```
$ cat inventory/targets/minikube-es.yml
classes:
  - cluster.minikube
  - component.elasticsearch

parameters:
  namespace: minikube-es

  elasticsearch:
    replicas: 2
```

Targets can also be defined inside the `inventory`.

# Typical folder structure

```
.
├── components
│   ├── elasticsearch
│   │   ├── configmap.jsonnet
│   │   ├── deployment.jsonnet
│   │   ├── main.jsonnet
│   │   └── service.jsonnet
│   └── nginx
│       ├── configmap.jsonnet
│       ├── deployment.jsonnet
│       ├── main.jsonnet
│       ├── nginx.conf.j2
│       └── service.jsonnet
├── inventory
│   ├── classes
│   │   ├── cluster
│   │   │   ├── cluster1.yml
│   │   │   └── cluster2.yml
│   │   ├── component
│   │   │   ├── elasticsearch.yml
│   │   │   ├── nginx.yml
│   │   │   └── zookeeper.yml
│   │   └── environment
│   │       ├── dev.yml
│   │       └── prod.yml
│   └── targets
│       ├── dev-cluster1-elasticsearch.yml
│       ├── prod-cluster1-elasticsearch.yml
│       └── prod-cluster2-frontend.yml
├── lib
│   ├── kapitan.libjsonnet
│   └── kube.libjsonnet
└── targets
    ├── dev-cluster1-elasticsearch
    │   └── target.yaml
    ├── prod-cluster1-elasticsearch
    │   └── target.yaml
    └── prod-cluster2-frontend
        └── target.yaml
```

# Usage

```
$ kapitan -h
usage: kapitan [-h] [--version] {eval,compile,inventory,searchvar,secrets} ...

Kapitan is a tool to manage kubernetes configuration using jsonnet templates

positional arguments:
  {eval,compile,inventory,searchvar,secrets}
                        commands
    eval                evaluate jsonnet file
    compile             compile targets
    inventory           show inventory
    searchvar           show all inventory files where var is declared
    secrets             manage secrets

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

Additional parameters are available for each positional argument. For example:

```
$ kapitan compile -h
usage: kapitan compile [-h] [--search-path JPATH] [--verbose] [--no-prune]
                       [--quiet] [--output-path PATH] [--target-path PATH]
                       [--parallelism INT] [--secrets-path SECRETS_PATH]
                       [--reveal] [--inventory-path INVENTORY_PATH]

optional arguments:
  -h, --help            show this help message and exit
  --search-path JPATH, -J JPATH
                        set search path, default is "."
  --verbose, -v         set verbose mode
  --no-prune            do not prune jsonnet output
  --quiet               set quiet mode, only critical output
  --output-path PATH    set output path, default is "."
  --target-path PATH    set target path, default is "./targets"
  --parallelism INT, -p INT
                        Number of concurrent compile processes, default is 4
  --secrets-path SECRETS_PATH
                        set secrets path, default is "./secrets"
  --reveal              reveal secrets (warning: this will write sensitive
                        data)
  --inventory-path INVENTORY_PATH
                        set inventory path, default is "./inventory"
```



# Modes of operation

### kapitan compile

This will compile all targets to `compiled` folder.

#### Using the inventory in jsonnet

Accessing the inventory from jsonnet compile types requires you to import `jsonnet/kapitan.libjsonnet`, which includes the native_callback functions glueing reclass to jsonnet (amongst others).

The jsonnet snippet below imports the inventory for the target you're compiling
and returns the java_opts for the elasticsearch data role:

```
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();

{
    "data_java_opts": inventory.parameters.elasticsearch.roles.data.java_opts,
}
```

#### Using the inventory in jinja2

Jinja2 types will pass the "inventory" and whatever target vars as context keys in your template.

This snippet renders the same java_opts for the elasticsearch data role:

```
java_opts for elasticsearch data role are: {{ inventory.parameters.elasticsearch.roles.data.java_opts }}
```


#### Jinja2 jsonnet templating

Such as reading the inventory within jsonnet, Kapitan also provides a function to render a Jinja2 template file. Again, importing "kapitan.jsonnet" is needed.

The jsonnet snippet renders the jinja2 template in templates/got.j2:

```
local kap = import "lib/kapitan.libjsonnet";

{
    "jon_snow": kap.jinja2_template("templates/got.j2", { is_dead: false }),
}
```

It's up to you to decide what the output is.


### kapitan inventory

Rendering the inventory for the _minikube-es_ target:

```
$ kapitan inventory -t minikube-es
...
classes:
  - cluster.common
  - cluster.minikube
  - component.elasticsearch
parameters:
  cluster:
    id: minikube
    name: minikube
    type: minikube
    user: minikube
  elasticsearch:
    image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
    java_opts: -Xms512m -Xmx512m
    masters: 1
    replicas: 2
    roles:
      client:
        image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
        java_opts: -Xms512m -Xmx512m
        masters: 1
        replicas: 2
      data:
        image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
        java_opts: -Xms512m -Xmx512m
        masters: 1
        replicas: 2
      ingest:
        image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
        java_opts: -Xms512m -Xmx512m
        masters: 1
        replicas: 2
      master:
        image: quay.io/pires/docker-elasticsearch-kubernetes:5.5.0
        java_opts: -Xms512m -Xmx512m
        masters: 1
        replicas: 2
  kapitan:
    compile:
      - input_paths:
          - components/elasticsearch/main.jsonnet
        input_type: jsonnet
        output_path: manifests
        output_type: yaml
      - input_paths:
          - scripts
        input_type: jinja2
        output_path: scripts
      - input_paths:
          - docs/elasticsearch/README.md
        input_type: jinja2
        output_path: .
    secrets:
      recipients:
        - dummy@recipient
    vars:
      namespace: minikube-es
      target: minikube-es
  kubectl:
    insecure_skip_tls_verify: false
  minikube:
    cpus: 4
    memory: 4096
    version: v0.25.0
  mysql:
    hostname: localhost
  namespace: minikube-es
  target_name: minikube-es
  vault:
    address: https://localhost:8200
```

### kapitan searchvar

show all inventory files where var is declared

```
$ kapitan searchvar parameters.elasticsearch.replicas
./inventory/targets/minikube-es-2.yml             2
./inventory/targets/minikube-es.yml               2
./inventory/classes/component/elasticsearch.yml   1
```



# Credits

* [Jsonnet](https://github.com/google/jsonnet)
* [Jinja2](http://jinja.pocoo.org/docs/2.9/)
* [reclass](https://github.com/madduck/reclass)

# FAQ

## Why do we prefer Kapitan to `Helm`?

Before developing Kapitan, we turned to [`Helm`](https://github.com/kubernetes/helm) in an attempt to improve from our old Jinja based templating system.

We quickly discovered that `Helm` did not fit well with our workflow, for the following reasons (which were true at the time of the evaluation):
* `Helm` uses Go templates to define Kubernetes (yaml) manifests. We were already unsatisfied by using Jinja and we did not see a huge improvement from our previous system, the main reason being: YAML files are not suitable to be managed by text templating frameworks.
* `Helm` does not have a solution for sharing values across charts, if not through subcharts. We wanted to be able to have one single place to define all values for all our templates. Sharing data between charts felt awkward and complicated.
* `Helm` is component/chart based. We wanted to have something that would treat the whole of our deployments as a whole.
* We did not fancy the dependency on the tiller.

In short, we feel `Helm` is trying to be `apt-get` for Kubernetes charts, while we are trying to take you further than that.

## Why do I need Kapitan?
With Kapitan, we worked to de-compose several problems that most of the other solutions are treating as one.

1) ***Kubernetes manifests***: We like the jsonnet approach of using json as the working language. Jsonnet allows us to use inheritance and composition, and hide complexity at higher levels.
2) ***Configuration files***: Most solutions will assume this problem is solved somewhere else. We feel Jinja (or your template engine of choice) have the upper hand here.
3) ***Hierarchical inventory***: This is the feature that sets us apart from other solutions. We use the inventory (based on [reclass](https://github.com/madduck/reclass)) to define variables and properties that can be reused across different projects/deployments. This allows us to limit repetition, but also to define a nicer interface with developers (or CI tools) which will only need to understand YAML to operate changes.
4) ***Canned scripts***: We treat scripts as text templates, so that we can craft pre-canned scripts for the specific target we are working on. This can be used for instance to define scripts that setup clusters, contexts or allow to run kubectl with all the correct settings. Most other solutions require you to define contexts and call kubectl with the correct settings. We take care of that for you. Less ambiguity, less mistakes.
5) ***Documentation***: We also use templates to create documentation for the targets we deploy. Documentation lived alongside everything else and it is treated as a first class citizen.
We feel most other solutions are pushing the limits of their capacity in order to provide for the above problems.
Helm treats everything as a text template, while jsonnet tries to do everything as json.
We believe that these approaches can be blended in a powerful new way, glued together by the inventory.


# Related projects

* [sublime-jsonnet-syntax](https://github.com/gburiola/sublime-jsonnet-syntax) - Jsonnet syntax highlighting for sublime text Edit

