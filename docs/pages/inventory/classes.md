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

!!! warning "Opt-in required"
    Wildcard expansion is **disabled by default**.  You must pass
    `--enable-class-wildcards` on the `kapitan compile` or `kapitan inventory`
    command (or set `enable-class-wildcards: true` under the
    `[inventory_backend]` section of `.kapitan`) to activate it.

    The flag is intentionally opt-in because inventories may contain glob
    metacharacters in class names for legitimate reasons — for example a class
    file literally named `config[html].yml`, or Reclass references that include
    `?` such as `${?some_parameter}`.  Without the flag those entries are passed
    through unchanged to the backend, which handles them normally.

```yaml
classes:
  - "*"             # all classes (top-level and nested) — quote required
  - clusters.*      # all classes whose dotted name starts with 'clusters.'
  - apps.dev-*      # all classes under apps/ whose basename starts with 'dev-'
  - "*.dev-*"       # any class with a 'dev-...' segment in any subdir
```

Supported glob characters are `*`, `?`, `[` and `]` (standard
[`fnmatch`](https://docs.python.org/3/library/fnmatch.html) syntax).

**Pattern semantics:**

* Patterns are matched against the **full dotted class name** using
  `fnmatch`. There is no special-case based on whether a pattern contains
  `.`. For example, `dev-*` matches only top-level classes named
  `dev-...`; to match `apps.dev-api` you must write `apps.dev-*` or
  `*.dev-*`.
* Class entries that look like Reclass / Kapitan parameter references —
  any string containing `${` and `}`, including `${var}` and `${?var}` —
  are passed through to the backend unchanged, even if they contain a
  glob metacharacter such as `?`. The wildcard expander cannot resolve
  such references; the backend handles them after class inheritance.
  Notably, this also means that pattern expansion isn't supported in
  class includes that use Reclass references.

**Exact-match precedence:**

When `--enable-class-wildcards` is on, the expander first checks whether a
`classes:` entry exactly matches an existing class name. If it does, the entry
is treated as a literal include even if the name contains glob metacharacters.
Only entries that do **not** match any existing class and that contain
metacharacters are expanded as patterns.

This means:

* A class file literally named `config[html].yml` can still be included with
  `- config[html]`. It will be treated as an exact class name, not as a
  character-class pattern.
* If you want `config[html]` to act as a pattern that matches `configh`,
  `configt`, `configm`, `configl`, you would need to remove the literal class
  file so there is no exact match.

**Deterministic lexicographic ordering:**

Each pattern expands to a **lexicographically sorted** list of matches at
the position of the pattern in the `classes:` list, giving deterministic
output.

!!! warning "Override order depends on class names"
    Lexicographic order is deterministic but can be surprising.  For example,
    a pattern `*.base` that matches both `config.base` and `defaults.base`
    will always expand to `[config.base, defaults.base]` because `c < d`.
    Whether `config.base` or `defaults.base` "wins" in a merge depends on the
    backend's evaluation order.

    **Adding a new class that matches an existing pattern can change the
    include order of previously matched classes.**  For example, if you later
    add `alpha.base`, the expansion of `*.base` becomes
    `[alpha.base, config.base, defaults.base]`, shifting the indices of
    `config.base` and `defaults.base`.  If another part of your inventory
    depends on those indices (unlikely but possible with some backends), the
    behavior changes.

    When wildcard expansion order is critical, design class names carefully.
    A safe convention is to use **numeric prefixes** that sort in the desired
    precedence order:

    ```yaml
    classes:
      - app.00-defaults
      - app.10-config
      - app.90-overrides
    ```

    This ensures that `app.*` always expands in the intended order regardless
    of what other `app.*` classes are added later.

    Avoid wildcards when merge order is critical and you cannot control
    class naming conventions.

* Duplicates (across exact entries and pattern expansions) are removed,
  preserving the first occurrence.
* A pattern that matches **no** classes raises an inventory error, unless
  `--ignore-class-not-found` is set, in which case the unmatched pattern is
  silently dropped (mirroring the behavior of exact missing class names).

**Symlink handling:**

Wildcard expansion materializes a temporary copy of the inventory tree using
`shutil.copytree(..., symlinks=True)`.  Symlinks that point to targets
**inside** the inventory tree are preserved and resolve correctly.  Relative
symlinks that point **outside** the inventory tree (a common pattern when
pulling in external modules, e.g. with Commodore) are rewritten to absolute
paths in the materialized copy so they continue to work.

!!! note
    `discover_classes` follows directory symlinks during class discovery, so
    classes inside symlinked directories are discoverable.  External directory
    symlinks are rewritten to absolute paths in the materialized copy, which
    also makes their contents discoverable.

!!! warning "`ignore_class_notfound_regexp` interaction"
    Wildcard expansion happens before the inventory backend processes missing
    classes.  If you use `ignore_class_notfound_regexp` in your reclass
    configuration, the regex is evaluated against each **expanded class name**, not
    against the original pattern string.  If you rely on regex-based skipping of
    pattern-like entries, you may need to adjust your regex or use
    `--ignore-class-not-found` instead.

Wildcard expansion happens before the backend resolves inheritance, and works
both in target files and in nested class files.

**Backend-specific notes:**

* The omegaconf backend's class-file resolver currently only looks for `.yml`
  files (a pre-existing limitation unrelated to wildcards).  Wildcard
  expansion correctly discovers `.yaml` classes, but omegaconf will fail to
  load them.


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
