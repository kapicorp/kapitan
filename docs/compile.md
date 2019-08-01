## Compile

### Usage

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

### Synopsis

This command compiles all targets to `compiled` folder. For each target, the 

