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

### Wildcard class patterns

Class entries may also be glob patterns that expand to the matching set of
classes discovered under `inventory/classes/`. This avoids having to list
each class individually when the set is large or grows over time
(see [issue #1084](https://github.com/kapicorp/kapitan/issues/1084)).

```yaml
classes:
  - "*"          # all classes (top-level and nested)
  - clusters.*   # all classes under inventory/classes/clusters/
  - dev-*        # all classes whose basename starts with dev-
```

Supported glob characters are `*`, `?`, `[` and `]` (standard
[`fnmatch`](https://docs.python.org/3/library/fnmatch.html) syntax).

Pattern semantics:

* A pattern that contains a `.` is matched against the **full** dotted class
  name (e.g. `clusters.*` matches `clusters.prod` and `clusters.dev` but not
  `common`).
* A pattern with no `.` is matched against the **basename segment** (the
  part after the last `.`), so `dev-*` matches both `dev-common` and
  `apps.dev-api`.

Other behavior:

* Both `.yml` and `.yaml` files are discovered.
* Hidden files/directories (names starting with `.`) and non-YAML files are
  ignored when expanding patterns.
* Each pattern expands to a **lexicographically sorted** list of matches at
  the position of the pattern in the `classes:` list, giving deterministic
  output.
* Duplicates (across exact entries and pattern expansions) are removed,
  preserving the first occurrence — this matches the order in which a user
  would expect classes to be merged.
* A pattern that matches **no** classes raises an inventory error, unless
  `--ignore-class-not-found` is set, in which case the unmatched pattern is
  silently dropped (mirroring the behavior of exact missing class names).

Wildcard expansion happens before reclass resolves inheritance, and works
both in target files and in nested class files.


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
