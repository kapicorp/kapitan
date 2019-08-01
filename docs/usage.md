### Usage

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
    secrets             manage secrets
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

#### Using `.kapitan` config file

These parameters can also be defined in a local `.kapitan` file, for example:

```
$ cat .kapitan

compile:
  indent: 4
  parallelism: 8
```

This is equivalent to running:

```
kapitan compile --indent 4 --parallelism 8
```

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

