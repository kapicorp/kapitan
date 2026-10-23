---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 4m
date: 2026-06-24
title: "Introducing Topics for Organising Kapitan Targets"
description: "A backend-agnostic way to expose, aggregate, and consume parameters across Kapitan targets, without cryptic reclass queries."
---

# Introducing Topics for Organising Kapitan Targets

Sometimes a target needs data from other targets: the list of databases
another target provisions, or the endpoints a dozen services expose. So far
the options were reclass exports, whose query syntax is hard to read and
which only exist in reclass, or `inventory_global()` in a component, which
loads every target to find a handful of values.

Topics, available since v0.36.0, take a simpler approach. A target publishes
selected parameters to a named topic, and other targets read the aggregated
topic, independent of the inventory backend.

<!-- more -->

!!! note "Changed in v0.36.2"
    A target that reads a topic must declare it with `consume: true`, as
    shown below. In v0.36.0 and v0.36.1 this declaration did not exist.

## Publishing to a topic

A target publishes by setting parameters under
`parameters.kapitan.topics.<topic_name>.parameters`. Two targets that each
publish a `colour` to the `colours` topic:

```yaml
# inventory/targets/target-1.yml
parameters:
  colour: red
  kapitan:
    topics:
      colours:
        parameters:
          colour: ${colour}
```

```yaml
# inventory/targets/target-2.yml
parameters:
  colour: blue
  kapitan:
    topics:
      colours:
        parameters:
          colour: ${colour}
```

A topic only carries what a target puts under it. Targets that do not
mention the topic contribute nothing, and no other parameters leak into it.
Kapitan aggregates the publishing targets into one view:

```yaml
parameters:
  targets:
    target-1:
      colour: red
    target-2:
      colour: blue
```

## Consuming a topic

A target that reads a topic declares it:

```yaml
# inventory/targets/painter.yml
parameters:
  kapitan:
    topics:
      colours:
        consume: true
```

The declaration makes the cross-target dependency explicit. When
`target-1` changes its colour, the painter's output changes even though the
painter's own inventory did not. The Kadet input cache includes a digest of
each declared topic in the consumer's cache key, so it does not serve stale
output. A target can publish to and consume the same topic by setting both
`parameters` and `consume: true` on it.

Reading an undeclared topic is a compile error that names the fix:

```
target 'painter' must declare the topic(s) it consumes. Add to its inventory:
  parameters.kapitan.topics.colours.consume: true
```

## Reading topics in components

`topics()` is available in every input type. With a name it returns that
topic; without arguments it returns all topics, in which case every topic
must be declared by the calling target. A declared topic that no target
publishes to returns an empty view with the same shape, so the loops below
iterate over nothing instead of failing.

In Kadet, import it from `kapitan.inputs.kadet` for attribute-style access:

```python
# components/painter/__init__.py
from kapitan.inputs.kadet import topics

def main():
    target_colours = {}
    for target, parameters in topics("colours").parameters.targets.items():
        target_colours[target] = {"colour": parameters.colour}
    return target_colours
```

In Jinja2, `topics` is part of the template context:

```jinja
{# components/painter.j2 #}
{% for target, parameters in topics("colours").parameters.targets.items() %}
{{ target }}:
  colour: {{ parameters.colour }}
{% endfor %}
```

In Jsonnet, it is exposed through the Kapitan library:

```jsonnet
// components/painter.jsonnet
local kap = import "lib/kapitan.libjsonnet";
{
  [target]: { colour: params.colour }
  for target in std.objectFields(kap.topics("colours").parameters.targets)
  for params in [kap.topics("colours").parameters.targets[target]]
}
```

All three produce the same data. With `output_type: yaml`, the Kadet and
Jsonnet versions write one file per key:

```yaml
# compiled/painter/target-1.yaml
colour: red
```

```yaml
# compiled/painter/target-2.yaml
colour: blue
```

## Inspecting topics from the CLI

`kapitan inventory --topics` prints all topics, and with a name only that
one:

```shell
kapitan inventory --topics colours
```

```yaml
parameters:
  targets:
    target-1:
      colour: red
    target-2:
      colour: blue
```

`--pattern` and `--flat` work as usual. `--pattern` normally requires a
target; with `--topics` it applies to the topic view instead:

```shell
kapitan inventory --topics colours --pattern parameters.targets
kapitan inventory --topics --flat
```

The CLI does not check `consume` declarations.

## Topics and reclass exports

Topics replace the common use of exports: collecting a value from a set of
targets. A target opts in, Kapitan aggregates, a component reads. There are
no queries, and aggregation happens in Kapitan's inventory layer, so it
works the same under reclass, reclass-rs and OmegaConf. Conditional
inventory queries and computed lookups still need reclass exports.

The full reference is in the
[advanced inventory documentation](../../inventory/advanced.md).
