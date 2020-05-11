# Remote Inventory Federation

This feature would add the ability to Kapitan to fetch parts of the inventory from remote locations (https/git). This would allow users to combine different inventories from different sources and build modular infrastructure reusable across various repos.


Author: @alpharoy14

## Specification

The configuration and declaration of remote inventories would be done in the hidden file `​.kapitan`.

The file specifications are as follows:

```yaml
remoteInventory:
    -   name: <inventory_name> #user defined
        type: <inventory_type> #git\https
        source: <source_of_inventory>
        output_path: <relative_output_path>
        ... type specific arguments
```
The command for adding remote inventories to the `.kapitan` file from cli will be:
```$ kapitan inventory --add <inventory-name> <output-path> <source> ```
The command for fetching remote inventories that is added to the `.kapitan` file will be:
``` $ kapitan inventory --fetch <inventory-name> ```
The command for fetching all the inventory declared in .kapitan file will be:

```$ kapitan inventory --fetch-all```

## Copying inventory files to the output location
The output path is the path to save the inventory items into. The path is relative to the `inventory/` directory. For example, it could be `/classes/`. The contents of the fetched inventory will be recursively copied.

The fetched inventory files will be cached in a temp directory.
The temp directory (`remote_inventories/`) will be in the path pointed by the $XDG_CACHE_HOME environment variable. In case that does not exist, we can check the `$KAPITAN_CACHE_DIR`. Which, by default, will be set to the root folder of the project.

## Force fetching
While fetching, the output path will be recursively checked to see if it contains any file with the same name. If so, kapitan will raise an error saying so.

To overwrite the files with the newly downloaded inventory items, we can add the --force flag to the fetch command, as shown below.

`$ kapitan inventory --fetch-all --force`
`$ kapitan inventory --fetch <inventory-name> --force`

## URL type
The URL type (Http/git) will be inferred from the <source> address. Depending on the URL type, the configuration file may have additional arguments.

E.g Git type may also include aditional `ref` parameter as illustrated below:

```yaml
remoteInventory:
    -   name: <inventory_name> #user defined
        type: <inventory_type> #git\https
        source: <source_of_inventory>
        output_path: <relative_output_path>
        ref: <commit_hash/branch/tag>
```

## Implementation details
TODO

### Dependencies

- [GitPython](https://github.com/gitpython-developers/GitPython) module (and git executable) for git type
- requests module for http[s]