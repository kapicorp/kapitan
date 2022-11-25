# :kapitan-logo: Inventory

## Overview

The **Inventory** is a core component of Kapitan: this section aims to explain how it works and how to best take advantage of it.

The **Inventory** is a hierarchical `YAML` based structure which you use to capture anything that you want to make available to **Kapitan**, so that it can be passed on to its templating engines.

The first concept to learn about the **Inventory** is the [**target**](#targets). A target is a file, found under the [`inventory/targets`](#targets) substructure, that tells Kapitan what you want to compile. It will usually map to something you want to do with **Kapitan**. 

For instance, you might want to define a [**target**](#targets) for each environment that you want to deploy using **Kapitan**. 

The **Inventory** lets you also define and reuse common configurations through YAML files that are referred to as [**classes**](#classes): by listing classes into [**target**](#targets), their content gets merged together and allows you to compose complex configurations without repetitions.

By combining [**target**](#targets) and [**classes**](#classes), the **Inventory** becomes the single source of truth (SSOT) for your whole configuration, and learning how to use it will unleash the real power of **Kapitan**.

!!! info
    The **Kapitan** **Inventory** is based on an open source project called [reclass](https://github.com/kapicorp/reclass) and you can find the full documentation on our Github clone. However we discourage you to look directly at the reclass documentation before you learn more about **Kapitan**, because **Kapitan** uses a fork of reclass and greatly simplifies the reclass experience.

!!! note
    Kapitan enforces very little structure for the **Inventory**, so that you can adapt it to your specific needs: this might be overwhelming at the beginning: don’t worry, we will explain best practice and give guidelines soon.

By default, Kapitan will search for its **Inventory** under [`inventory/classes`](#classes) and [`inventory/targets`](#targets).

```
inventory/
├── classes
│   ├── applications
│   ├── components
│   ├── features
│   ├── kapitan
│   ├── projects
│   └── terraform
└── targets
    ├── examples
    ├── kapicorp
    └── terraform
```

## Targets

### Usage

A target is a file that lives under the [`inventory/targets`](#targets) subdirectory, and that tells **Kapitan** what you want it to do for you.

 **Kapitan** will recognise all YAML files in the [`inventory/targets`](#targets) subtree as targets.

!!! note
    Only use **`.yml`** as extension for **Inventory** files. `.yaml` will not be recognised as a valid **Inventory** file.

What you do with a [**target**](#targets) is largely up to you and your setup. Common examples:

  * **clusters**: Each target to map to a cluster you have, and used to caputure all configurations needed for a given cluster. For instance `targets/clusters/production-cluster1.yml`
  * **applications**: When using **Kapitan** to manage **Kubernetes** applications, is to use a [**target**](#targets) file to define everything that you would normally deploy in a single namespace, including all its resources, scripts, secrets and documentation. For instance `targets/mysql.yaml`
  * **environments**: You might have want to define a different [**target**](#targets) for each environment you have, like `dev.yml`, `test.yml` and `prod.yml`
  * **cloud projects**: When working with **Terraform**, you could find it convenient to group in a [**target**](#targets) all resource definitions needed for a given cloud project.
  * **single tenancy**: When working on deploying a single-tenancy application, you might combine the approaches above, and have a [**target**](#targets) `acme.yml` that is used to define both **Terraform** and **Kubernetes** resources for a given tenant, perhaps also with some **ArgoCD** or **Spinnaker** pipelines to go with it.


!!! example

    If you have configured your kapitan repository like in [Quick Start](/kapitan_overview/#setup-your-repository) instructions, you can run the commands we give during the course of this documentation.

    !!! quote ""

        `kapitan compile`

    ```shell
    Compiled gke-pvm-killer (0.09s)
    Compiled vault (0.18s)
    Compiled pritunl (0.17s)
    Compiled mysql (0.07s)
    Compiled examples (0.25s)
    Compiled postgres-proxy (0.06s)
    Compiled echo-server (0.08s)
    Compiled global (0.05s)
    Compiled tutorial (0.09s)
    Compiled guestbook-argocd (0.08s)
    Compiled sock-shop (0.30s)
    Compiled kapicorp-demo-march (0.04s)
    Compiled kapicorp-project-123 (0.03s)
    Compiled kapicorp-terraform-admin (0.08s)
    Compiled tesoro (0.09s)
    Compiled prod-sockshop (0.34s)
    Compiled dev-sockshop (0.41s)
    Compiled argocd (2.53s)
    ```

    When you run `kapitan compile`, you instruct **Kapitan** will generate, for each given [**target**](#targets), a directory under `compiled` with the same name: under this directory you will find all the files that have been generated by **Kapitan** for that target.

    !!! quote ""

        `tree compiled/mysql/`

    ```shell
    compiled/mysql/
    ├── argocd
    ├── docs
    │   ├── mysql-readme.md
    │   └── README.md
    ├── manifests
    │   ├── mysql-bundle.yml
    │   ├── mysql-config.yml
    │   ├── mysql-namespace.yml
    │   └── mysql-secret.yml
    ├── pre-deploy
    ├── rabbitmq
    ├── scripts
    └── terraform

    7 directories, 6 files
    ```

### Definition

A tipical [**target**](#targets) might looks like this:

!!! example "`inventory/targets/acme/dev.yaml`"

    ```yaml
    classes:
      - common
      - components.acme.frontend
      - components.acme.backend

    parameters:
      target_name: dev
    ```

Note that it is made of 2 sections:

* `classes` is a list of class files you will want to import.
* `parameters` allows for local override of what is unique to this target. 

!!! info

    the `kapitan` key under the root `parameters` is reserved for kapitan usage. Some examples:

    ```yaml
    parameters:
      kapitan:
        compile:      # input types configuration section
        dependencies: # dependencies configuration section to download resources
        secrets:      # secret encryption/decryption configuration section
        validate:     # items which indicate which compiled output to validate
        vars:         # which are also passed down to input types as context
    ```


## Classes

### Usage

The next thing you want to learn about the inventory are [**classes**](#classes). A class is a yaml file containing a fragment of yaml that we want to import and merge into the inventory.

[**Classes**](#classes) are *fragments* of yaml: feature sets, commonalities between targets. [**Classes**](#classes) let you compose your [**Inventory**](#inventory) from smaller bits, eliminating duplication and exposing all important parameters from a single, logically organised place. As the [**Inventory**](#inventory) lets you reference other parameters in the hierarchy, [**classes**](#classes) become places where you can define something that will then get referenced from another section of the inventory, allowing for composition.

[**Classes**](#classes) are organised under the [`inventory/classes`](#classes) directory substructure. 
They are organised hierarchically in subfolders, and the way they can be imported into a [**target**](#targets) or other [**classes**](#classes) depends on their location relative to the [`inventory/classes`](#classes) directory.


### Importing classes

To import a class from within another file of the [**Inventory**](#inventory), you can follow these instructions:

* take the file path relative to the `inventory/classes/` directory
* remove the `.yml` file extension
* replace `/` with `.`

For example, this will import the class `inventory/classes/applications/sock-shop.yaml`

```yaml
classes:
- applications.sock-shop
```

### Definition
Let's take a look at the `common` class which appears in the example above:

As explained, because the **`common.yaml`** is directly under the **`inventory/classes`** subdirectory, it can be imported directly into a target with:

```yaml
classes:
- common
```

If we open the file, we find another familiar yaml fragment.

!!! example "`inventory/classes/common.yml`"

    ```yaml
    classes:
    - kapitan.common

    parameters:
      namespace: ${target_name}
      target_name: ${_reclass_:name:short}
    ```

Notice that this class includes an import definition for another class, `kapitan.common`. We've already learned this means that kapitan will import a file on disk called `inventory/classes/kapitan/common.yml`

You can also see that in the `parameters` section we now encounter a new syntax which unlocks another powerful inventory feature: *parameters interpolation*!

## Parameters Interpolation

!!! note

    as a shorthand, when we encounter deep yaml structures like the following:

    ```yaml
    parameters:
      components:
        nginx:
          image: nginx:latest
    ``` 

    Usually when we want to talk about the `image` subkey, we normally use either of the following: 
    
      * `parameters.components.nginx.image`
      * `components.nginx.image`

    However, when used in parameter expansion, remember to:
    
      * replace the `.` with `:` 
      * omit the `parameters` initial key which is implied
      * wrap it into the `${}` variable interpolation syntax

    The correct way to reference `parameters.nginx.image` then becomes `${components:nginx:image}`. 

The [**Inventory**](#inventory) allows you to refer to other values defined elsewhere in the structure, using parameter interpolation.

Given the example:

```yaml

parameters:
  cluster:
    location: europe
  
  application:
    location: ${cluster:location}

  namespace: ${target_name}
  target_name: dev
```



Here we tell **Kapitan** that:

* `namespace` should take the same value defined in `target_name`
* `target_name` should take the literal string `dev`
* `application.location` should take the same value as defined in `cluster.location`

It is important to notice that the inventory can refer to values defined in other classes, as long as they are imported by the target. So for instance with the following example

```yaml

classes:
  - project.production

  parameters:
    application:
      location: ${cluster.location}
```

Here in this case `application.location` refers to a value `location` which has been defined elsewhere, perhaps (but not necessarily) in the `project.production` class.

Also notice that the class name (`project.production`) is not in any ways influencing the name or the structed of the yaml it imports into the file

## Advanced Inventory Features

### Remote Inventories

Kapitan is capable of recursively fetching inventory items stored in remote locations and copy it to the specified output path. This feature can be used by specifying those inventory items in classes or targets under `parameters.kapitan.inventory`. Supported types are:

- [git type](#git-type)
- [http type](#http-type)

#### Commands
Use the `--fetch` flag to fetch the remote inventories and the external dependencies.

```shell
kapitan compile --fetch
```

This will download the dependencies and store them at their respective `output_path`.
By default, kapitan does not overwrite an existing item with the same name as that of the fetched inventory items.

Use the `--force-fetch` flag to force fetch (update cache with freshly fetched items) and overwrite inventory items of the same name in the `output_path`.

```shell
kapitan compile --force-fetch
```

Use the `--cache` flag to cache the fetched items in the `.dependency_cache` directory in the root project directory.

```shell
kapitan compile --cache --fetch
```

Class items can be specified before they are locally available as long as they are fetched in the same run. [Example](#example) of this is given below.

#### Git type

Git types can fetch external inventories available via HTTP/HTTPS or SSH URLs. This is useful for fetching repositories or their sub-directories, as well as accessing them in specific commits and branches (refs).

**Note**: git types require git binary on your system.

##### Usage

```yaml
parameters:
  kapitan:
    inventory:
    - type: git
      output_path: path/to/dir
      source: git_url
      subdir: relative/path/from/repo/root (optional)
      ref: tag, commit, branch etc. (optional)
```

##### Example

Lets say we want to fetch a class from our kapitan repository, specifically
`kapicorp/kapitan/tree/master/examples/docker/inventory/classes/dockerfiles.yml`. 

Lets create a simple target file `docker.yml`

!!! example ""

    !!! note 

        [external dependencies](external_dependencies.md) are used to fetch dependency items in this example.

    !!! example "`targets/docker.yml`"


        ```yaml
        classes:
          - dockerfiles
        parameters:
          kapitan:
            vars:
              target: docker
            inventory:
              - type: git
                source: https://github.com/kapicorp/kapitan
                subdir: examples/docker/inventory/classes/
                output_path: classes/
            dependencies:
              - type: git
                source: https://github.com/kapicorp/kapitan
                subdir: examples/docker/components
                output_path: components/
              - type: git
                source: https://github.com/kapicorp/kapitan
                subdir: examples/docker/templates
                output_path: templates/
          dockerfiles:
          - name: web
            image: amazoncorretto:11
          - name: worker
            image: amazoncorretto:8
        ```

    !!! example ""

        ```shell
        kapitan compile --fetch
        ```

    ??? example "click to expand output" 
        ```shell
        [WARNING] Reclass class not found: 'dockerfiles'. Skipped!
        [WARNING] Reclass class not found: 'dockerfiles'. Skipped!
        Inventory https://github.com/kapicorp/kapitan: fetching now
        Inventory https://github.com/kapicorp/kapitan: successfully fetched
        Inventory https://github.com/kapicorp/kapitan: saved to inventory/classes
        Dependency https://github.com/kapicorp/kapitan: saved to components
        Dependency https://github.com/kapicorp/kapitan: saved to templates
        Compiled docker (0.11s)
        ```



#### http type

`http[s]` types can fetch external inventories available at `http://` or `https://` URL.

##### definition

```yaml
parameters:
  kapitan:
    inventory:
    - type: http | https
      output_path: full/path/to/file.yml
      source: http[s]://<url>
      unpack: True | False # False by default
```

##### Example

!!! example ""


    !!! example "`targets/mysql-generator-fetch.yml`"


        ```yaml
        classes:
          - common
          - kapitan.generators.kubernetes
        parameters:
          kapitan:
            inventory:
              - type: https
                source: https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml
                output_path: classes/kapitan/generators/kubernetes.yml
          components:
            mysql:
              image: mysql
        ```

    !!! example ""

        ```shell
        kapitan compile --fetch
        ```

    ??? example "click to expand output" 
        ```shell
        ./kapitan compile -t mysql-generator-fetch --fetch
        Inventory https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml: fetching now
        Inventory https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml: successfully fetched
        Inventory https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml: saved to inventory/classes/kapitan/generators/kubernetes.yml
        
        ...
        cut
        ...

        Compiled mysql-generator-fetch (0.06s)
        ```
