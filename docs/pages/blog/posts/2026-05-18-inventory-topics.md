---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 5m
date: 2026-05-18
title: "Introducing Topics for Organising Kapitan Targets"
description: "A backend-agnostic way to expose, aggregate, and consume parameters across Kapitan targets, without cryptic reclass queries."
---

# :kapitan-logo: **Introducing Topics for Organising Kapitan Targets**

Every so often a target needs to know something about its neighbours. One target wants the list of every database another target provisions; a dashboard wants the endpoints exposed by a dozen services. Until now the answers were either reclass exports (powerful, but the query syntax makes our eyes water) or a full `inventory_global()` scan in a component (works, but it reads *everything* just to find a handful of values).

We wanted something simpler: let a target say "here is the bit I'm willing to share", and let other targets collect those bits without caring which inventory backend is underneath. That's what **topics** are.

<!-- more -->

## Opting in

A target joins a topic by declaring parameters under `parameters.kapitan.topics.<topic_name>.parameters`. Nothing else needs wiring up. Here are two targets that both publish a `colour` into a `colours` topic:

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

The key detail: a topic only ever carries what a target *explicitly* puts under it. A target that never mentions `topics` contributes nothing and pays no cost. There's no scanning, no opt-out, no surprise leakage of unrelated parameters.

Kapitan aggregates every participating target into one view, shaped like this:

```yaml
parameters:
  targets:
    target-1:
      colour: red
    target-2:
      colour: blue
```

A third target that doesn't touch `colours` simply won't appear. That's the whole model.

## Inspecting topics from the CLI

Before you write any component, you can look at the aggregated result directly. The `inventory` subcommand grew a `--topics` flag:

```shell
kapitan inventory --topics
```

That dumps every topic. Pass a name to narrow it down to one:

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

It composes with the flags you already know. `--pattern` drills into the structure, and `--flat` gives you flat dotted keys:

```shell
kapitan inventory --topics colours --pattern parameters.targets
kapitan inventory --topics --flat
```

!!! note
    `--pattern` normally needs a target name. With `--topics` that requirement is relaxed, since the topic view is the thing you're drilling into.

## Consuming a topic in a component

There's a new `topics()` function, and it's available to every input type. Call it with no arguments for the full mapping, or with a name for a single topic.

In **kadet**, import it from `kapitan.inputs.kadet` and you get attribute-style access:

!!! example "`components/painter/__init__.py`"
    ```python
    from kapitan.inputs.kadet import topics

    def main():
        target_colours = {}
        for target, parameters in topics("colours").parameters.targets.items():
            target_colours[target] = {"colour": parameters.colour}
        return target_colours
    ```

In **jinja2**, `topics` is injected into the template context:

!!! example "`components/painter.j2`"
    ```jinja
    {% for target, parameters in topics("colours").parameters.targets.items() %}
    {{ target }}:
      colour: {{ parameters.colour }}
    {% endfor %}
    ```

And in **jsonnet**, it's exposed through the Kapitan library:

!!! example "`components/painter.jsonnet`"
    ```jsonnet
    local kap = import "lib/kapitan.libjsonnet";
    {
      [target]: { colour: params.parameters.colour }
      for target in std.objectFields(kap.topics("colours").parameters.targets)
      for params in [kap.topics("colours").parameters.targets[target]]
    }
    ```

All three compile to the same thing:

```yaml
target-1:
  colour: red
target-2:
  colour: blue
```

If you ask for a topic that nobody publishes to, you don't get an exception. You get an empty but well-shaped result, so `topics("nope").parameters.targets.items()` just iterates over nothing. We'd rather your component degrade quietly than blow up on a typo.

## Why we built it this way

The honest motivation was reclass exports. They solve the cross-target problem, but the query expressions are hard to reason about and they tie you to one backend. Topics are deliberately dumber: a target opts in, Kapitan collects, a component reads. No queries, no backend-specific behaviour, and it works the same under reclass, reclass-rs, and omegaconf.

It won't replace exports for every case. If you need conditional inventory queries or computed lookups, reclass still has more reach. But for the common "let me gather a value from a set of targets" job, topics are a lot less to think about. Give them a spin with `kapitan inventory --topics` and see what your targets are willing to share.
