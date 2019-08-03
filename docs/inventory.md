# Inventory

## Overview

Inventory is a hierarchical database of variables that are passed to the targets during compilation.

By default, Kapitan will look for an `inventory/` directory to render the inventory from.

There are 2 types of objects inside the inventory; [inventory classes](#inventory-classes) and [inventory targets](#inventory-targets). 

### Inventory Classes

Classes define variables that are shared across many targets. You can have, for example, a `component.elasticsearch` class with all the default values for targets using elasticsearch. Or a `production` or `dev` class to enable / disable certain features based on the type of target.

You can always override values further up the tree (i.e. in the inventory target file or in a class that inherits another class)

Classifying almost anything will help you avoid repetition (DRY) and will force you to organise parameters hierarchically.

#### Example: elasticsearch

For example, the snippet below, taken from the example `elasticsearch` class, declares
what parameters are needed for the elasticsearch component:

```
$ cat inventory/classes/component/elasticsearch.yml
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
      client:
        image: ${elasticsearch:image}
        java_opts: ${elasticsearch:java_opts}
        replicas: ${elasticsearch:replicas}
        masters: ${elasticsearch:masters}
      ingest:
        image: ${elasticsearch:image}
        java_opts: ${elasticsearch:java_opts}
        replicas: ${elasticsearch:replicas}
        masters: ${elasticsearch:masters}
```

As shown above, within the inventory, you can refer to the values with the syntax `${obj_name:key_name}` (no need to specify the `parameters` key).

#### Example: mysql

Or in the `mysql` class example, we declare the generic variables that will be shared by all targets that import the component and what to compile.

We include a secret that is referencing a GPG encrypted value in `secrets/targets/minikube-mysql/mysql/password`, or if the file doesn't exist, it will dynamically generate a random b64-encoded password, encrypt it and save it into the file.

```
$ cat inventory/classes/component/mysql.yml
parameters:
  mysql:
    storage: 10G
    storage_class: standard
    image: mysql:latest
    users:
      root:
        # If 'secrets/targets/${target_name}/mysql/password' doesn't exist, it will gen a random b64-encoded password
        password: ?{gpg:targets/${target_name}/mysql/password|randomstr|base64}
        # password: ?{gkms:targets/${target_name}/mysql/password|randomstr|base64}
        # password: ?{awskms:targets/${target_name}/mysql/password|randomstr|base64}

        # Generates the sha256 checksum of the previously declared B64'ed password
        # It's base64'ed again so that it can be used in kubernetes secrets
        password_sha256: ?{gpg:targets/${target_name}/mysql/password_sha256|reveal:targets/${target_name}/mysql/password|sha256|base64}
  kapitan:
    compile:
    - output_path: manifests
      input_type: jsonnet
      input_paths:
        - components/mysql/main.jsonnet
      output_type: yaml
    - output_path: scripts
      input_type: jinja2
      input_paths:
        - scripts
    - output_path: .
      output_type: yaml
      input_type: jinja2
      input_paths:
        - docs/mysql/README.md
```

### Inventory Targets

A target usually represents a single namespace in a kubernetes cluster and defines all components, scripts and documentation that will be generated for that target. Kapitan will recognise files in `inventory/targets` as targets.

When you run `kapitan compile`, kapitan will generate `compiled` directory whose sub-directories are named after the targets, each of which contains all the compiled output defined under `parameters.kapitan.compile` for a target.

Inside the inventory target files you can include classes and define new values or override any values inherited from the included classes.
For example:

```
$ cat inventory/targets/minikube-es.yml
classes:
  - common
  - cluster.minikube
  - component.elasticsearch

parameters:
  target_name: minikube-es

  elasticsearch:
    replicas: 2
```

Targets can also be defined inside the `inventory`. 

**Note**: Each target must contain the property `parameters.kapitan.vars.target` whose value equals to the name of the target file. For example, for the target `inventory/targets/minikube-es.yml`, the rendered inventory must contain:

```yaml
parameters:
  kapitan:
    vars:
      target: minikube-es
```

### kapitan-specific inventory values: `parameters.kapitan`

Values under `parameters.kapitan`, such as `parameters.kapitan.vars` as mentioned above, are special values that kapitan parses and processes. These include:

- `kapitan.compile` items which indicate which files to compile
- `kapitan.secrets` which contains secret encryption/decryption information
- `kapitan.validate` items which indicate which compiled output to validate
- `kapitan.vars` which are also passed down to jsonnet and jinja2 templates as contexts

## Useful commands

### kapitan inventory

Renders the resulting inventory values for a specific target.

For example, rendering the inventory for the `minikube-es` target:

```shell
$ kapitan inventory -t minikube-es
...
classes:
  - component.namespace
  - cluster.common
  - common
  - cluster.minikube
  - component.elasticsearch
environment: base
exports: {}
parameters:
  _reclass_:
    environment: base
    name:
      full: minikube-es
      short: minikube-es
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
          - components/namespace/main.jsonnet
        input_type: jsonnet
        output_path: pre-deploy
        output_type: yaml
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
      gpg:
        recipients:
          - fingerprint: D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C
            name: example@kapitan.dev
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

Use `kapitan lint` to checkup on your inventory/secrets.

### kapitan searchvar

Shows all inventory files where a variable is declared:

```
$ kapitan searchvar parameters.elasticsearch.replicas
./inventory/targets/minikube-es.yml               2
./inventory/classes/component/elasticsearch.yml   1
```

