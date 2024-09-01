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

### Command line flags

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

For flags which are shared by multiple commands, you can either selectively define them for single commmands in a section with the same name as the command, or you can set any flags in section `global`, in which case they're applied for all commands.
If you set a flag in both the `global` section and a command's section, the value from the command's section takes precedence over the value from the global section.

As an example, you can configure the `inventory-path` in the `global` section of the **Kapitan** dotfile to make sure it's persisted across all **Kapitan** runs.

```yaml
...

global:
  inventory-path: ./some_path
```

which would be equivalent to running any command with `--inventory-path=./some_path`.

Another flag that you may want to set in the `global` section is `inventory-backend` to select a non-default inventory backend implementation.

```yaml
global:
  inventory-backend: reclass
```

which would be equivalent to always running **Kapitan** with `--inventory-backend=reclass`.

Please note that the `inventory-backend` flag currently can't be set through the command-specific sections of the **Kapitan** config file.
