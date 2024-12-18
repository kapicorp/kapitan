# Classes

## Usage

The next thing you want to learn about the inventory are [**classes**]. A class is a yaml file containing a fragment of yaml that we want to import and merge into the inventory.

**Classes** are *fragments* of yaml: feature sets, commonalities between targets. **Classes** let you compose your [**Inventory**](introduction.md) from smaller bits, eliminating duplication and exposing all important parameters from a single, logically organised place. As the [**Inventory**](introduction.md)  lets you reference other parameters in the hierarchy, [**classes**] become places where you can define something that will then get referenced from another section of the inventory, allowing for composition.

**Classes** are organised under the [`inventory/classes`] directory substructure.
They are organised hierarchically in subfolders, and the way they can be imported into a [**target**](targets.md) or other [**classes**] depends on their location relative to the [`inventory/classes`] directory.


### Importing classes

To import a class from within another file of the [**Inventory**](introduction.md), you can follow these instructions:

* take the file path relative to the `inventory/classes/` directory
* remove the `.yml` file extension
* replace `/` with `.`

For example, this will import the class `inventory/classes/applications/sock-shop.yaml`

```yaml
classes:
- applications.sock-shop
```

## Definition

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
