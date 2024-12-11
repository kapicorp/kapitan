
# :kapitan-logo: **Targets**

In the world of Kapitan, a target represents a specific environment or deployment scenario where you want to apply your configurations.

Think of it as a blueprint that defines all the necessary settings and parameters for a particular deployment.

For instance, you might have separate targets for **`production`**, **`staging`**, and **`development`** environments, each with its own unique configurations.

## Defining targets
Targets are defined as YAML files within the `inventory/targets/` directory of your Kapitan project. Each target file typically includes:

```
classes:
    # A list of classes to inherit configurations from.
    # This allows you to reuse common settings and avoid repetition
    -

parameters:
    # file parameters that override or extend the parameters inherited from previously loaded classes
```

Example:

```yaml
# inventory/targets/production/web.yml
classes:
  - common
  - components.nginx

parameters:
  environment: production
  description: ${environment} environment
  nginx:
    replicas: 3
  namespace: ${environment}
```

In this example, the `production.web` target:

* Inherits configurations from the common and components.nginx classes.
* Sets the `environment` parameter to **`production`**.
* Overrides (if defined) the `replicas` for the `nginx` component to `3`.
* Defines the namespace as **`production`** using variable interpolation.
* Creates a dynamic description based on the content of the environment variable.

## Compiling targets
When you run kapitan compile -t <target_name>, Kapitan:

* Reads the target file: Kapitan parses the YAML file for the specified target.
* Merges configurations: It merges the parameters from the included classes with the target-specific parameters, giving priority to the target's values.
* Generates output in `compiled/target/path/targetname`: It uses this merged configuration data, along with the input types and generators, to create the final configuration files for the target environment.

When you run `kapitan` without the selector, it will run compile for all targets it discovers under the `inventory/targets` subdirectory.

## Target directory structure
Targets are not limited to living directly within the `inventory/targets` directory.

They can be organized into subdirectories to create a more structured and hierarchical inventory. This is particularly useful for managing large and complex projects.

When targets are organized in subdirectories, Kapitan uses the full path from the `targets/` directory to create the target name. This name is then used to identify the target during compilation and in the generated output.

Example for target `clusters.production.my-cluster`

```shell
inventory/
└── targets/
    └── clusters/
        └── production/
            └── my-cluster.yml
```

In this example, the `my-cluster.yml` target file is located within the `clusters/production/` subdirectory, and can be identified with `clusters.production.my-cluster`.
