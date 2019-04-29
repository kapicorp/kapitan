# Kapitan: Generic templated configuration management for Kubernetes, Terraform and other things

[![Build Status](https://travis-ci.org/deepmind/kapitan.svg?branch=master)](https://travis-ci.org/deepmind/kapitan)

Kapitan is a tool to manage complex deployments using jsonnet, [kadet (alpha)](https://github.com/deepmind/kapitan/pull/190) and jinja2.

Use Kapitan to manage your Kubernetes manifests, your documentation, your Terraform configuration or even simplify your scripts.

Join our community on [`#kapitan`](https://kubernetes.slack.com) or visit [**`https://kapitan.dev`**](https://kapitan.dev)


How is it different from [`Helm`](https://github.com/kubernetes/helm)? Please look at our [FAQ](#faq)!

<img src="./docs/kapitan_logo.png" width="250">

# Table of Contents

* [Main Features](#main-features)
* [Quickstart](#quickstart)
* [Example](#example)
* [Main concepts](#main-concepts)
* [Typical folder structure](#typical-folder-structure)
* [Usage](#usage)
* [Modes of operation](#modes-of-operation)
* [CI](#ci)
* [Contributing](#contributing)
* [Credits](#credits)
* [FAQ](#faq)
* [Related projects](#related-projects)

# Main Features

* Use the Inventory as the single source of truth to tie together deployments, resources and documentation. [based on reclass](https://github.com/salt-formulas/reclass)
* Use [Jsonnet](https://jsonnet.org/) or [Kadet (alpha)](https://github.com/deepmind/kapitan/pull/190) to create json/yaml based configurations (e.g. Kubernetes, Terraform);
* Use [Jinja2](http://jinja.pocoo.org/) to create text based templates for scripts and documentation;
* Manage secrets with GPG or gCloud KMS and define who can access them, without compromising collaboration with other users.
* Create dynamically generated documentation about a single deployment (i.e. ad-hoc instructions) or all deployments at once (i.e. global state of deployments)



# Quickstart

#### Docker (recommended)

```
docker run -t --rm -v $(pwd):/src:delegated deepmind/kapitan -h
```

On Linux you can add `-u $(id -u)` to `docker run` to preserve file permissions.

For CI/CD usage, check out our [ci instructions](#ci)

#### Pip

Kapitan needs Python 3.6.

**Install Python 3.6:**

 * Linux: `sudo apt-get update && sudo apt-get install -y python3.6-dev python3-pip python3-yaml`
 * Mac: `brew install python3 libyaml`

**Install Kapitan:**

User (`$HOME/.local/lib/python3.6/bin` on Linux or `$HOME/Library/Python/3.6/bin` on macOS):

```shell
pip3 install --user --upgrade kapitan
```

System-wide (not recommended):

```shell
sudo pip3 install --upgrade kapitan
```

# Example

The example below _compiles_ 3 targets inside the `examples/kubernetes` folder.
Each target represents a different namespace in a minikube cluster

These targets generate the following resources:

* Kubernetes `Namespace` for the targets
* Kubernetes `StatefulSet` for ElasticSearch Master node
* Kubernetes `StatefulSet` for ElasticSearch Client node
* Kubernetes `StatefulSet` for ElasticSearch Data node
* Kubernetes `Service` to expose ElasticSearch discovery port
* Kubernetes `Service` to expose ElasticSearch service port
* Kubernetes `StatefulSet` for MySQL
* Kubernetes `Service` to expose MySQL service port
* Kubernetes `Secret` for MySQL credentials
* Scripts to configure kubectl context to control the targets and helpers to apply/delete objects.
* Documentation

![demo](./docs/demo.gif)

```shell
$ cd examples/kubernetes

$ kapitan compile
Compiled minikube-mysql
Compiled minikube-es
```

# Main concepts

<img src="./docs/kapitan_overview.png" width="600">

### Components

A component is an application that will be deployed to a kubernetes cluster. This includes all necessary kubernetes objects (StatefulSet, Services, ConfigMaps) defined in jsonnet or kadet.
It may also include scripts, config files and dynamically generated documentation defined using Jinja templates.

### Inventory

This is a hierarchical database of variables that are passed to the targets during compilation.

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
├── secrets
│   ├── targets
│   │   ├── prod-cluster1-elasticsearch
│   │   │   └── password
│   ├── common
│   │   └── example-com-tls.key
├── lib
    ├── kapitan.libjsonnet
    └── kube.libjsonnet
```

# Usage

Use `kapitan init --directory <directory>` to populate a new
directory with the recommended kapitan folder structure in new projects.

For other available options use:

```
$ kapitan -h
usage: kapitan [-h] [--version]
               {eval,compile,inventory,searchvar,secrets,lint} ...

Generic templated configuration management for Kubernetes, Terraform and other
things

positional arguments:
  {eval,compile,inventory,searchvar,secrets,lint,init}
                        commands
    eval                evaluate jsonnet file
    compile             compile targets
    inventory           show inventory
    searchvar           show all inventory files where var is declared
    secrets             manage secrets
    lint                linter for inventory and secrets
    init                initialize a directory with the recommended kapitan
                        project skeleton.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

```

Additional parameters are available for each positional argument. For example:

```
$ kapitan compile -h
usage: kapitan compile [-h] [--search-paths JPATH [JPATH ...]] [--verbose]
                       [--prune] [--quiet] [--output-path PATH]
                       [--targets TARGET [TARGET ...]] [--parallelism INT]
                       [--indent INT] [--secrets-path SECRETS_PATH] [--reveal]
                       [--inventory-path INVENTORY_PATH] [--cache]
                       [--cache-paths PATH [PATH ...]]
                       [--ignore-version-check]

optional arguments:
  -h, --help            show this help message and exit
  --search-paths JPATH [JPATH ...], -J JPATH [JPATH ...]
                        set search paths, default is ["."]
  --jinja2-filters FPATH, -J2F FPATH
                        load custom jinja2 filters from any file, default is
                        to put them inside lib/jinja2_filters.py
  --verbose, -v         set verbose mode
  --prune               prune jsonnet output
  --quiet               set quiet mode, only critical output
  --output-path PATH    set output path, default is "."
  --targets TARGET [TARGET ...], -t TARGET [TARGET ...]
                        targets to compile, default is all
  --parallelism INT, -p INT
                        Number of concurrent compile processes, default is 4
  --indent INT, -i INT  Indentation spaces for YAML/JSON, default is 2
  --secrets-path SECRETS_PATH
                        set secrets path, default is "./secrets"
  --reveal              reveal secrets (warning: this will write sensitive
                        data)
  --inventory-path INVENTORY_PATH
                        set inventory path, default is "./inventory"
  --cache, -c           enable compilation caching to .kapitan_cache, default
                        is False
  --cache-paths PATH [PATH ...]
                        cache additional paths to .kapitan_cache, default is
                        []
  --ignore-version-check
                        ignore the version from .kapitan
```

These parameters can also be defined in a local `.kapitan` file, for example:

```shell
$ cat .kapitan

compile:
  indent: 4
  parallelism: 8
```

This is equivalent to running:

```shell
kapitan compile --indent 4 --parallelism 8
```

To enforce the kapitan version used for compilation (for consistency and safety), you can add `version` to `.kapitan`:

```shell
$ cat .kapitan
version: 0.21.0
```

Or to skip all minor version checks:
```shell
$ cat .kapitan
version: 0.21
```


# Modes of operation

### kapitan compile

This will compile all targets to `compiled` folder.

#### Using the inventory in jsonnet

Accessing the inventory from jsonnet compile types requires you to import `jsonnet/kapitan.libjsonnet`, which includes the native_callback functions glueing reclass to jsonnet (amongst others).

Available native_callback functions are:
```
yaml_load - returns a json string of the specified yaml file
yaml_dump - returns a string yaml from a json string
file_read - reads the file specified
jinja2_render_file - renders the jinja2 file with context specified
sha256_string - returns sha256 of string
gzip_b64 - returns base64 encoded gzip of obj
inventory - returns a dictionary with the inventory for target
```

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

Such as reading the inventory within jsonnet, Kapitan also provides a function to render a Jinja2 template file. Again, importing `kapitan.jsonnet` is needed.

The jsonnet snippet renders the jinja2 template in templates/got.j2:

```
local kap = import "lib/kapitan.libjsonnet";

{
    "jon_snow": kap.jinja2_template("templates/got.j2", { is_dead: false }),
}
```

It's up to you to decide what the output is.

#### Jinja2 custom filters

We support the following custom filters for use in Jinja2 templates:

```
sha256 - SHA256 hashing of text e.g. {{ text | sha256 }}
yaml - Dump text as YAML e.g. {{ text | yaml }}
b64encode - base64 encode text e.g. {{ text | b64encode }}
b64decode - base64 decode text e.g. {{ text | b64decode }}
fileglob - return list of matched regular files for glob e.g. {{ ./path/file* | fileglob }}
bool - return the bool for value e.g. {{ yes | bool }}
to_datetime - return datetime object for string e.g. {{ "2019-03-07 13:37:00" | to_datetime }}
strftime - return current date string for format e.g. {{ "%a, %d %b %Y %H:%M" | strftime }}
regex_replace - perform a re.sub returning a string e.g. {{ hello world | regex_replace(pattern="world", replacement="kapitan") }}
regex_escape - escape all regular expressions special characters from string e.g. {{ "+s[a-z].*" | regex_escape }}
regex_search - perform re.search and return the list of matches or a backref e.g. {{ hello world | regex_search("world.*") }}
regex_findall - perform re.findall and return the list of matches as array e.g. {{ hello world | regex_findall("world.*") }}
ternary - value ? true_val : false_val e.g. {{ condition | ternary("yes", "no") }}
shuffle - randomly shuffle elements of a list {{ [1, 2, 3, 4, 5] | shuffle }}
```
You can also provide path to your custom filter modules in CLI. By default you can put your filters in lib/jinja2_filters.py and they will automatically get loaded.

### kapitan secrets

Manages your secrets with GPG, Google Cloud KMS (beta) or AWS KMS (beta), with plans to also support Vault.

If you want to get started with secrets but don't have a GPG or KMS setup, you can use the secret ref type. Note that `ref` is not encrypted and is intented for development purposes only. *Do not use `ref` secrets if you're storing sensitive information!*

The usual flow of creating and using an encrypted secret with kapitan is:

- Define your GPG recipients or KMS key, see [common.yml class](./examples/kubernetes/inventory/classes/common.yml), `parameters.kapitan.secrets`. You can also define these per target.

- Create your secret:

  - Manually:
    ```
    GPG: kapitan secrets --write gpg:targets/minikube-mysql/mysql/password -t minikube-mysql -f <password file>
    gKMS: kapitan secrets --write gkms:targets/minikube-mysql/mysql/password -t minikube-mysql -f <password file>
    awsKMS: kapitan secrets --write awskms:targets/minikube-mysql/mysql/password -t minikube-mysql -f <password file>
    ref: kapitan secrets --write ref:targets/minikube-mysql/mysql/password -t minikube-mysql -f <password file> # WARNING: ref is not encrypted and intended for dev use only
    OR use stdin:
    echo -n '<password>' | kapitan secrets --write [gpg/gkms/awskms]:targets/minikube-mysql/mysql/password -t minikube-mysql -f -
    ```
    This will inherit the secrets configuration from minikube-mysql target, encrypt and save your password into `secrets/targets/minikube-mysql/mysql/password`, see `examples/kubernetes`.

  - Automatically:<br>
    See [mysql.yml class](./examples/kubernetes/inventory/classes/component/mysql.yml). When referencing your secret, you can use the following functions to automatically generate, encrypt and save your secret:
    ```
    randomstr - Generates a random string. You can optionally pass the length you want i.e. `|randomstr:32`
    base64 - base64 encodes your secret; to be used as a secondary function i.e. `|randomstr|base64`
    sha256 - sha256 hashes your secret; to be used as a secondary function i.e. `|randomstr|sha256`. You can optionally pass a salt i.e `|randomstr|sha256:salt` -> becomes `sha256("salt:<generated random string>")`
    reveal - Decrypts a secret; to be used as a secondary function, useful for reuse of a secret like for different encodings i.e `|reveal:path/to/secret|base64`
    rsa - Generates an RSA 4096 private key (PKCS#8). You can optionally pass the key size i.e. `|rsa:2048`
    rsapublic - Derives an RSA public key from a revealed private key i.e. `|reveal:path/to/encrypted_private_key|rsapublic`
    ```
    **Note:** If you use `|reveal:/path/secret`, when changing the `/path/secret` file make sure you also delete any secrets referencing `/path/secret` so kapitan can regenerate them.

- Use your secret in your classes/targets, like in the [mysql.yml class](./examples/kubernetes/inventory/classes/component/mysql.yml):
  ```
  users:
    root:
      # If 'secrets/targets/${target_name}/mysql/password' doesn't exist, it will gen a random b64-encoded password
      password: ?{gpg:targets/${target_name}/mysql/password|randomstr|base64}
  ```

- After `kapitan compile`, this will compile to the [mysql_secret.yml k8s secret](./examples/kubernetes/compiled/minikube-mysql/manifests/mysql_secret.yml). If you are part of the GPG recipients, you can see the secret by running:
  ```
  kapitan secrets --reveal -f compiled/minikube-mysql/manifests/mysql_secret.yml
  ```

To setup GPG for the kubernetes examples you can run:

```shell
gpg --import examples/kubernetes/secrets/example\@kapitan.dev.pub
gpg --import examples/kubernetes/secrets/example\@kapitan.dev.key
```

And to trust the GPG example key:

```shell
gpg --edit-key example@kapitan.dev
gpg> trust
Please decide how far you trust this user to correctly verify other users' keys
(by looking at passports, checking fingerprints from different sources, etc.)
1 = I don't know or won't say
2 = I do NOT trust
3 = I trust marginally
4 = I trust fully
5 = I trust ultimately
m = back to the main menu
Your decision? 5
Do you really want to set this key to ultimate trust? (y/N) y
gpg> quit
```

### kapitan inventory

Rendering the inventory for the `minikube-es` target:

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

Show all inventory files where a variable is declared:

```
$ kapitan searchvar parameters.elasticsearch.replicas
./inventory/targets/minikube-es.yml               2
./inventory/classes/component/elasticsearch.yml   1
```
# Continuous Integration

See [CI.md](docs/CI.md).

# Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

# Credits

* [Jsonnet](https://github.com/google/jsonnet)
* [Jinja2](http://jinja.pocoo.org/docs/2.9/)
* [reclass](https://github.com/salt-formulas/reclass)

# FAQ

## Why do we prefer Kapitan to `Helm`?

Before developing Kapitan, we turned to [`Helm`](https://github.com/kubernetes/helm) in an attempt to improve our old Jinja based templating system.

We quickly discovered that `Helm` did not fit well with our workflow, for the following reasons (which were true at the time of the evaluation):
* `Helm` uses Go templates to define Kubernetes (yaml) manifests. We were already unsatisfied by using Jinja and we did not see a huge improvement from our previous system, the main reason being: YAML files are not suitable to be managed by text templating frameworks.
* `Helm` does not have a solution for sharing values across charts, if not through subcharts. We wanted to be able to have one single place to define all values for all our templates. Sharing data between charts felt awkward and complicated.
* `Helm` is component/chart based. We wanted to have something that would treat all our deployments as a whole.
* We did not fancy the dependency on the tiller.

In short, we feel `Helm` is trying to be `apt-get` for Kubernetes charts, while we are trying to take you further than that.

## Why do I need Kapitan?
With Kapitan, we worked to de-compose several problems that most of the other solutions are treating as one.

1) ***Kubernetes manifests***: We like the jsonnet approach of using json as the working language. Jsonnet allows us to use inheritance and composition, and hide complexity at higher levels.

2) ***Configuration files***: Most solutions will assume this problem is solved somewhere else. We feel Jinja (or your template engine of choice) have the upper hand here.

3) ***Hierarchical inventory***: This is the feature that sets us apart from other solutions. We use the inventory (based on [reclass](https://github.com/salt-formulas/reclass)) to define variables and properties that can be reused across different projects/deployments. This allows us to limit repetition, but also to define a nicer interface with developers (or CI tools) which will only need to understand YAML to operate changes.

4) ***Secrets***: We manage most of our secrets with kapitan using the GPG, Google Cloud KMS and AWS KMS integrations. Keys can be setup per class, per target or shared so you can easily and flexibly manage access per environment. They can also be dynamically generated on compilation, if you don't feel like generating random passwords or RSA private keys, and they can be referenced in the inventory like any other variables. We have plans to support other providers such as Vault, in addition to GPG, Google Cloud KMS and AWS KMS.

5) ***Canned scripts***: We treat scripts as text templates, so that we can craft pre-canned scripts for the specific target we are working on. This can be used for instance to define scripts that setup clusters, contexts or allow running kubectl with all the correct settings. Most other solutions require you to define contexts and call kubectl with the correct settings. We take care of that for you. Less ambiguity, less mistakes.

6) ***Documentation***: We also use templates to create documentation for the targets we deploy. Documentation lived alongside everything else and it is treated as a first class citizen.
We feel most other solutions are pushing the limits of their capacity in order to provide for the above problems.
Helm treats everything as a text template, while jsonnet tries to do everything as json.
We believe that these approaches can be blended in a powerful new way, glued together by the inventory.


# Related projects

* [sublime-jsonnet-syntax](https://github.com/gburiola/sublime-jsonnet-syntax) - Jsonnet syntax highlighting for Sublime Text
* [language-jsonnet](https://github.com/google/language-jsonnet) - Jsonnet syntax highlighting for Atom
* [vim-jsonnet](https://github.com/google/vim-jsonnet) - Jsonnet plugin for Vim (requires a vim plugin manager)
