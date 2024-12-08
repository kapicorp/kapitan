# The reclass-rs inventory backend

## Overview

[Reclass-rs](https://github.com/projectsyn/reclass-rs) is a reimplementation of Kapitan's Reclass fork in Rust.
Please note that the Rust implementation doesn't support all the features of Kapitan's Reclass fork yet.

However, reclass-rs improves rendering time for the inventory significantly, especially if you're making heavy use of parameter references in class includes.
If some of the Reclass features or options that you're using are missing in reclass-rs, don't hesitate to open an issue in the [reclass-rs project](https://github.com/projectsyn/reclass-rs/issues/new?assignees=&labels=enhancement&projects=&template=03_missing_reclass_feature.md).

## Installation

The `reclass-rs` Python package is an optional dependency of Kapitan.
You can install it as follows:

```shell
pip install kapitan[reclass-rs]
```

## Usage

To use the reclass-rs inventory backend, you need to pass `--inventory-backend=reclass-rs` on the command line.
If you want to permanently switch to the reclass-rs inventory backend, you can select the inventory backend in the [.kapitan config file](../commands/kapitan_dotfile.md):

```yaml
global:
  inventory-backend: reclass-rs
```

## Performance comparison

For the performance comparison, a real Kapitan inventory which makes heavy use of parameter interpolation in class includes was rendered with both Reclass and reclass-rs.
The example inventory that was used for the performance comparison contains 325 classes and 56 targets.
The example inventory renders to a total of 25MB of YAML.

### Reclass

```
$ time kapitan inventory -v --inventory-backend=reclass > inv.yml
[ ... some output omitted ... ]
kapitan.resources DEBUG    Using reclass as inventory backend
kapitan.inventory.backends.reclass DEBUG    Inventory reclass: No config file found. Using reclass inventory config defaults
kapitan.inventory.backends.reclass DEBUG    Inventory rendering with reclass took 0:01:06.037057

real    1m23.840s
user    1m23.520s
sys     0m0.287s
```

Reclass takes 1 minute and 6 seconds to render the example inventory.
The rest of the runtime (roughly 18 seconds) is spent in writing the resulting 25MB of YAML to the output file.

### reclass-rs

```
$ time kapitan inventory -v --inventory-backend=reclass-rs > inv-rs.yml
[ ... some output omitted ... ]
kapitan.resources DEBUG    Using reclass-rs as inventory backend
kapitan.inventory.backends.reclass DEBUG    Inventory reclass: No config file found. Using reclass inventory config defaults
reclass-config.yml entry 'storage_type=yaml_fs' not implemented yet, ignoring...
reclass-config.yml entry 'inventory_base_uri=./inventory' not implemented yet, ignoring...
reclass-config.yml entry 'allow_none_override=true' not implemented yet, ignoring...
kapitan.inventory.backends.reclass_rs DEBUG    Inventory rendering with reclass-rs took 0:00:01.717107

real    0m19.921s
user    0m35.586s
sys     0m1.066s
```

reclass-rs takes 1.7 seconds to render the example inventory.
The rest of the runtime (roughly 18 seconds) is spent in writing the resulting 25MB of YAML to the output file.
