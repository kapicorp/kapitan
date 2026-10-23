---
title: "Kapitan Advanced Inventory: Labels and Backends"
description: "Discover advanced Kapitan inventory features such as target labels and selectors to group, filter, and organize your targets."
---

# Advanced Inventory Features

## Target labels

Kapitan allows you to define labels in your inventory, which can then be used to group together targets with similar labels.

For instance you could define the following:

!!! example ""

    Defines a class to add the `customer` label to selected targets

    !!! example "`inventory/classes/type/customer_project.yml`"
        ```yaml
        parameters:
          customer_name: ${target_name} # Defaults to the target_name
          kapitan:
            labels:
              customer: ${customer_name}
        ```

    Apply the class to the target for customer `acme`
    !!! example "`inventory/targets/customers/acme.yml`"

        ```yaml
        classes:
        ...
        - type.customer_project

        parameters:
        ...
        ```

    You can now selectively compile targets for customer `acme` using the following (see see [**Labels**](../commands/kapitan_compile.md#using-labels) for more details )

    !!! example ""

        ```shell
        kapitan compile -l customer=acme
        Compiled acme (0.06s)
        Compiled acme-documentation (0.09s)
        ```

## Topics

Topics let targets expose a subset of their parameters so that other targets can
aggregate and consume them, without resorting to backend-specific features like
reclass exports or expensive `inventory_global()` scans.

A target's relationship to a topic has two independent sides — **produce**
and **consume** — both declared under
`parameters.kapitan.topics.<topic_name>` on the same node.

**Producers** declare `parameters:` to publish a slice of their own
configuration into the topic:

!!! example "`inventory/targets/target-1.yml`"
    ```yaml
    parameters:
      colour: red
      kapitan:
        topics:
          colours:
            parameters:
              colour: ${colour}
    ```

!!! example "`inventory/targets/target-2.yml`"
    ```yaml
    parameters:
      colour: blue
      kapitan:
        topics:
          colours:
            parameters:
              colour: ${colour}
    ```

**Consumers** declare `consume: true` to opt into reading a topic. This is
required — calling `topics("colours")` from a target that has not declared
`consume: true` on the `colours` node is a compile error.

!!! example "`inventory/targets/painter.yml`"
    ```yaml
    parameters:
      kapitan:
        topics:
          colours:
            consume: true
    ```

A target can be both producer and consumer of the same topic — just declare
`parameters:` and `consume: true` together on the same node.

Why the explicit consumer declaration? Topics introduce a *cross-target*
dependency that is otherwise invisible: if `target-1` changes its colour,
the painter's output changes even though the painter's own inventory did
not. Without an explicit opt-in, the input cache would serve stale results
because it has no way to know which producers a given consumer depends on.
Declaring `consume: true` turns that hidden dependency into an explicit one,
and the kadet input cache (see `kapitan/inputs/cache.py`) mixes a digest of
each declared topic's aggregated view into the consumer's cache key.

Kapitan aggregates participating targets into a single topic view of the shape
`{parameters: {targets: {<target_name>: <topic_parameters>}}}`. The `topics()`
function is available to every input type (kadet, jinja2, jsonnet). Call it
without arguments to get the full mapping of all topics, or with a name to get
a single topic — in both cases every topic that would be returned must be
declared `consume: true` on the calling target.

!!! example "kadet (`components/painter/__init__.py`)"
    ```python
    from kapitan.inputs.kadet import topics

    def main():
        target_colours = {}
        for target, parameters in topics("colours").parameters.targets.items():
            target_colours[target] = {"colour": parameters.colour}
        return target_colours
    ```

!!! example "jinja2 (`components/painter.j2`)"
    ```jinja
    {% for target, parameters in topics("colours").parameters.targets.items() %}
    {{ target }}:
      colour: {{ parameters.colour }}
    {% endfor %}
    ```

!!! example "jsonnet (`components/painter.jsonnet`)"
    ```jsonnet
    local kap = import "lib/kapitan.libjsonnet";
    {
      [target]: { colour: params.parameters.colour }
      for target in std.objectFields(kap.topics("colours").parameters.targets)
      for params in [kap.topics("colours").parameters.targets[target]]
    }
    ```

This compiles into:

```yaml
target-1:
  colour: red
target-2:
  colour: blue
```

Topics are inventory-backend agnostic and only collect what each target
explicitly opts into, avoiding cryptic query expressions and full inventory
scans.

### Inspecting topics from the CLI

The `inventory` subcommand has a `--topics` flag for inspecting the aggregated
view without compiling anything.

!!! example "List all topics"
    ```shell
    kapitan inventory --topics
    ```

!!! example "Show a single topic"
    ```shell
    kapitan inventory --topics colours
    ```

`--topics` combines with `--pattern` to drill into the result and with `--flat`
to produce flat keys:

```shell
kapitan inventory --topics colours --pattern parameters.targets
kapitan inventory --topics --flat
```
---

## Next steps

- Review the [inventory introduction](introduction.md) for a refresher on targets and classes.
- Learn about [inventory backends](backends.md) such as reclass-rs and OmegaConf.
- Explore the [`kapitan compile` CLI reference](../commands/kapitan_compile.md#using-labels) for more label options.
