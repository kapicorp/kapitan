---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 7m
date: 2026-04-24
title: "A Deep Dive into the Kapitan OmegaConf Backend"
description: "How the OmegaConf inventory backend extends reclass with richer interpolation, custom resolvers, and the new literal escape syntax."
---

# :kapitan-logo: **A Deep Dive into the Kapitan OmegaConf Backend**

Reclass has been Kapitan's inventory engine for years, and it does the job. But every now and then we hit a wall: we want a default value, a tiny bit of conditional logic, or a key that resolves differently depending on where it gets merged. With reclass you reach for Jinja or a Kadet helper to paper over the gap. The OmegaConf backend closes a lot of those gaps inside the inventory itself.

It's still flagged experimental, so we won't pretend it's a drop-in replacement for every reclass setup. But the interpolation story is genuinely nicer, and a recent change (#1445) tidied up the one corner that always tripped people: how to emit a literal `${...}` without Kapitan trying to resolve it.

<!-- more -->

## Turning it on

The backend ships behind an extra, so install it first:

```shell
pip install kapitan[omegaconf]
```

Then either pass the flag per run:

```shell
kapitan compile --inventory-backend=omegaconf
```

…or make it the default in your `.kapitan` dotfile so you don't have to remember:

```yaml
global:
  inventory-backend: omegaconf
```

One small but welcome detail: the OmegaConf backend resolves class files with either `.yml` or `.yaml` extensions, with `.yml` winning if both happen to exist. Reclass only ever looked for `.yml`, so if you've inherited a tree full of `.yaml` files this just works now (that fix landed in #1483).

## Interpolation that reads like code

Here's where the difference shows up. Reclass references look like `${path:to:key}` with colons. OmegaConf uses dot notation, which lines up with how you'd write the path in your head:

```yaml
# inventory/targets/my-app.yml
parameters:
  app_name: my-application
  environment: production

  full_name: ${app_name}-${environment}   # → "my-application-production"

  config:
    database:
      host: db.example.com
      port: 5432

  db_url: "postgresql://${config.database.host}:${config.database.port}"
  # → "postgresql://db.example.com:5432"
```

Defaults come for free via OmegaConf's native resolvers, no Jinja required:

```yaml
parameters:
  timeout: ${oc.select:custom_timeout, 30}   # 30 unless custom_timeout is set
  log_level: ${oc.env:LOG_LEVEL, INFO}        # read from the environment
```

And there's a small toolbox of conditional and transformation resolvers on top — `if`, `ifelse`, `equal`, `merge`, `dict`, `yaml`, and friends. We won't list them all here; the [OmegaConf backend docs](../inventory/omegaconf.md) have the full table. The point is that a chunk of logic that used to live in templates can now live in the inventory, where it's easier to follow.

## Deferred evaluation, or "resolve later"

This is the feature we keep coming back to. Sometimes you want a value that doesn't resolve where it's *written*, but where it ends up after merging. OmegaConf does this with a **double-pass** strategy: the first pass resolves normal `${...}` interpolations, and a second pass picks up anything that was escaped as `\${...}` (now unescaped).

The classic case is a template whose name should match the key it's merged under:

```yaml
# inventory/classes/base-deployment.yml
parameters:
  deployment_template:
    name: \${parentkey:}      # deferred — resolves AFTER merge
    namespace: ${namespace}    # resolves immediately

# inventory/targets/my-app.yml
parameters:
  namespace: production
  deployments:
    web-frontend: ${deployment_template}
    api-backend: ${deployment_template}
```

The result:

```yaml
deployments:
  web-frontend:
    name: web-frontend       # from \${parentkey:}
    namespace: production
  api-backend:
    name: api-backend        # from \${parentkey:}
    namespace: production
```

One template, two different `name` values, no copy-paste. The `\${...}` escape here means "don't resolve me yet" — it is *not* a way to print a literal dollar sign. That distinction matters, and it's exactly what the next section is about.

## The literal escape: `${escape:...}`

Here's the corner that used to confuse everyone. Say you're generating Terraform and you want the compiled output to literally contain `${google_service_account.cluster.email}` — a Terraform reference, not something Kapitan should touch. Reaching for `\${...}` doesn't help, because under the double-pass model that backslash just defers resolution to the second pass; the interpolation still fires.

PR #1445 repurposed the `escape` resolver to do exactly this. `${escape:content}` emits `${content}` verbatim, protected from *both* resolution passes:

```yaml
parameters:
  cluster: my-cluster

  terraform_ref: ${escape:google_service_account.cluster.email}
  shell_home: ${escape:HOME}

  # Works mid-string too — surrounding interpolations still resolve
  greeting: "Hello ${escape:USER}, welcome to ${cluster}"
```

Compiled output:

```yaml
terraform_ref: ${google_service_account.cluster.email}
shell_home: ${HOME}
greeting: "Hello ${USER}, welcome to my-cluster"
```

The mechanism is pleasingly blunt. `escape_interpolation` doesn't return a `${...}` string (which would just get re-resolved on the second pass) — it wraps the content in opaque marker strings, `__KAPITAN_LITERAL__...__KAPITAN_LITERAL_END__`. Only after both OmegaConf passes finish does a final post-processing step swap those markers back for `${content}`. The neat side effect: the escaped content is safe even when it happens to collide with a real inventory key.

```yaml
parameters:
  environment: dev
  escaped_key: ${escape:environment}   # → "${environment}", NOT "dev"
```

!!! note "Two different escapes"
    `\${...}` means *deferred* — resolve on the second pass. `${escape:...}` means *literal* — never resolve, emit the `${...}` text as-is. They look similar and do opposite things. If you want a `${...}` in your compiled output, you want `escape`.

For expressions with commas or quotes — say a Terraform conditional — wrap the argument in single quotes so OmegaConf parses it as one piece:

```yaml
parameters:
  terraform_expression: ${escape:'var.foo == "bar" ? 1 : 0'}
  # → var.foo == "bar" ? 1 : 0
```

## Custom resolvers, when the built-ins run out

If the stock resolvers don't cover your case, drop a `resolvers.py` in your inventory directory and register your own. They're plain Python functions:

```python
# inventory/resolvers.py

def get_suffix(name: str) -> str:
    """Extract the bit after the last hyphen."""
    return name.split("-")[-1]

def pass_resolvers():
    return {"get_suffix": get_suffix}
```

```yaml
parameters:
  app_name: my-service
  suffix: ${get_suffix:${app_name}}   # → "service"
```

Resolvers can also take a special `_root_` argument to reach the whole inventory, which is how you build things like target-aware Vault references. Handy, but a reminder to keep them small — a resolver that does too much is just a template wearing a disguise.

## Migrating an existing inventory

You don't have to rewrite everything by hand. Point the `--migrate` flag at your tree and Kapitan rewrites the common reclass patterns for you:

```shell
kapitan compile --inventory-backend=omegaconf --migrate
```

It handles the obvious translations — `${path:to:key}` becomes `${path.to.key}`, `${_reclass_...}` becomes `${_kapitan_...}`, and any `\${escaped}` you were using purely as literal output becomes `${escape:escaped}`.

!!! danger "Back up first"
    `--migrate` rewrites files in place. Commit your inventory to version control before you run it, so reverting is a `git checkout` away.

A couple of things migration won't do for you: keys containing literal dots need the `access` resolver, and reclass features like `exports` and inventory queries aren't supported yet. So check the diff, don't just trust it.

## Should you switch?

If your inventory is mostly static data, reclass is fine and you can keep it. The OmegaConf backend earns its keep when you find yourself fighting the inventory — wanting a default, a conditional, a self-naming template, or a clean way to pass a literal `${...}` through to Terraform. The interpolation is more expressive, the `${escape:...}` story is finally unambiguous, and `--migrate` gets you most of the way across.

It's experimental, so kick the tyres on a branch first. If something breaks, [tell us](https://github.com/kapicorp/kapitan/issues/new/choose) — that feedback is what moves it out of experimental.
