# Usage

To see all the available commands, run:

```
$ kapitan -h
usage: kapitan [-h] [--version]
               {eval,compile,inventory,searchvar,secrets,lint} ...

Generic templated configuration management for Kubernetes, Terraform and other
things

positional arguments:
  {eval,compile,inventory,searchvar,secrets,lint,init,validate}
                        commands
    eval                evaluate jsonnet file
    compile             compile targets
    inventory           show inventory
    searchvar           show all inventory files where var is declared
    refs                manage secrets
    lint                linter for inventory and secrets
    init                initialize a directory with the recommended kapitan
                        project skeleton.
    validate            validate the compile output against schemas as
                        specified in inventory

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

```

Additional parameters are available for each positional argument. For example:

```
$ kapitan compile -h
usage: kapitan compile [-h] [--search-paths JPATH [JPATH ...]]
                       [--jinja2-filters FPATH] [--verbose] [--prune]
                       [--quiet] [--output-path PATH] [--fetch] [--validate]
                       [--parallelism INT] [--indent INT]
                       [--refs-path REFS_PATH] [--reveal]
                       [--inventory-path INVENTORY_PATH] [--cache]
                       [--cache-paths PATH [PATH ...]]
                       [--ignore-version-check] [--schemas-path SCHEMAS_PATH]
                       [--targets TARGET [TARGET ...] | --labels
                       [key=value [key=value ...]]]

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
  --fetch               fetch remote inventories and/or external dependencies
  --force               overwrite existing inventory and/or dependency item
  --validate            validate compile output against schemas as specified
                        in inventory
  --parallelism INT, -p INT
                        Number of concurrent compile processes, default is 4
  --indent INT, -i INT  Indentation spaces for YAML/JSON, default is 2
  --refs-path REFS_PATH
                        set refs path, default is "./refs"
  --reveal              reveal refs (warning: this will potentially write
                        sensitive data)
  --inventory-path INVENTORY_PATH
                        set inventory path, default is "./inventory"
  --cache, -c           enable compilation caching to .kapitan_cache and
                        dependency caching to .dependency_cache, default
                        is False
  --cache-paths PATH [PATH ...]
                        cache additional paths to .kapitan_cache, default is
                        []
  --ignore-version-check
                        ignore the version from .kapitan
  --schemas-path SCHEMAS_PATH
                        set schema cache path, default is "./schemas"
  --yaml-multiline-string-style STYLE
                        set multiline string style to STYLE, default is 'double-quotes'
  --yaml-dump-null-as-empty
                        dumps all none-type entries as empty, default is dumping as 'null'
  --targets TARGET [TARGET ...], -t TARGET [TARGET ...]
                        targets to compile, default is all
  --labels [key=value [key=value ...]], -l [key=value [key=value ...]]
                        compile targets matching the labels, default is all
```

## Selective target compilation

If you only want to compile a subset or specific targets, you can use the two kapitan compile flags `--targets, -t` or `--labels, -l`.

#### Specific target(s)

```
$ cd examples/kubernetes
$ kapitan compile -t minikube-mysql
Compiled minikube-mysql (0.43s)
```

#### Using labels

```
$ cd examples/kubernetes

$ cat inventory/classes/component/nginx-kadet.yml  # Inherited by minikube-nginx-kadet target
parameters:
  ...
  kapitan:
    ...
    labels:
      type: kadet

$ kapitan compile -l type=kadet
Compiled minikube-nginx-kadet (0.14s)
```

## Using `.kapitan` config file

These parameters can also be defined in a local `.kapitan` file per project directory, for example:


To enforce the kapitan version used for compilation (for consistency and safety), you can add `version` to `.kapitan`:

```
$ cat .kapitan
version: 0.21.0
```

Or to skip all minor version checks:

```
$ cat .kapitan
version: 0.21
```

You can also permanently define all command line flags in the `.kapitan` config file. For example:

```
$ cat .kapitan
version: 0.21

compile:
  indent: 4
  parallelism: 8
```

would be equivalent to running:

```
kapitan compile --indent 4 --parallelism 8
```

or

```
$ cat .kapitan
version: 0.21

inventory:
  inventory-path: ./some_path
```

which would be equivalent to always running:

```
kapitan inventory --inventory-path=./some_path
```
