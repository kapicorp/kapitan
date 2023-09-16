# :kapitan-logo: **CLI Reference** | `.kapitan` config file

## `.kapitan`

Kapitan allows you to coveniently override defaults by specifying a local `.kapitan` file in the root of your repository (relative to the kapitan configuration):

This comes handy to make sure **Kapitan** runs consistently for your specific setup.

!!! info
    Any **Kapitan** command can be overridden in the `.kapitan` dotfile, but here are some of the most common examples.

### `version`

To enforce the **Kapitan** version used for compilation (for consistency and safety), you can add `version` to `.kapitan`:

```yaml
version: 0.30.0

...
```

This constrain can be relaxed to allow minor versions to be also accepted:

```yaml
version: 0.30 # Allows any 0.30.x release to run

...
```

### `compile`

You can also permanently define all command line flags in the `.kapitan` config file. For example:

```yaml
...

compile:
  indent: 4
  parallelism: 8
```

would be equivalent to running:

```shell
kapitan compile --indent 4 --parallelism 8
```

### inventory

In some cases, you might want to store the inventory under a different directory. You can configure the `inventory` section of the **Kapitan** dotfile to make sure it's persisted across all **Kapitan** runs.

```yaml
...

inventory:
  inventory-path: ./some_path
```

which would be equivalent to always running:

```shell
kapitan inventory --inventory-path=./some_path
```
