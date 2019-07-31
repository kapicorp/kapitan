# Inventory Structure

Inventory is a hierarchical database of variables that are passed to the targets during compilation.

By default, Kapitan will look for an `inventory/` directory to render the inventory from.

There are 2 types of objects inside the inventory:

#### Inventory Classes

Classes define variables that are shared across many targets. You can have for example a `component.elasticsearch` class with all the default values for targets using elasticsearch. Or a `production` or `dev` class to enable / disable certain features based on the type of target.

You can always override values further up the tree (i.e. in the inventory target file or in a class that inherits another class)

Classifying almost anything will help you avoid repetition (DRY) and will force you to organise parameters hierarchically.

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

#### Inventory Targets

A target usually represents a single namespace in a kubernetes cluster and defines all components, scripts and documentation that will be generated for that target.

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