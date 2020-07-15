# Remote Inventory Federation

This feature would add the ability to Kapitan to fetch parts of the inventory from remote locations (https/git). This would allow users to combine different inventories from different sources and build modular infrastructure reusable across various repos.

Author: @alpharoy14

## Specification

The configuration and declaration of remote inventories would be done in the inventory files.

The file specifications are as follows:

```yaml
parameters:
 kapitan:
  inventory:
   - type: <inventory_type> #git\https
     source: <source_of_inventory>
     output_path: <relative_output_path>
```

On executing the ``` $ kapitan compile --fetch``` command, first the remote inventories will be fetched followed by fetching of external dependencies and finally merge the inventory to compile.


## Copying inventory files to the output location
The output path is the path to save the inventory items into. The path is relative to the `inventory/` directory. For example, it could be `/classes/`. The contents of the fetched inventory will be recursively copied.

The fetched inventory files will be cached in the `.dependency_cache` directory.

## Force fetching
While fetching, the output path will be recursively checked to see if it contains any file with the same name. If so, kapitan will skip fetching it.

To overwrite the files with the newly downloaded inventory items, we can add the `--force` flag to the compile command, as shown below.

`$ kapitan compile --fetch --force`

## URL type
The URL type can be either git or http(s). Depending on the URL type, the configuration file may have additional arguments.

E.g Git type may also include aditional `ref` parameter as illustrated below:

```yaml
inventory:
 - type: git #git\https
   source: <source_of_inventory>
   output_path: <output_path>
   ref: <commit_hash/branch/tag>
```

## Implementation details
TODO

### Dependencies

- [GitPython](https://github.com/gitpython-developers/GitPython) module (and git executable) for git type
- requests module for http[s]