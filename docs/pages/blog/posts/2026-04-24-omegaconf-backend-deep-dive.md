---
author: The Kapitan Team
author_gh_user: kapicorp
read_time: 5m
date: 2026-04-24
title: "A Deep Dive into the Kapitan OmegaConf Backend"
description: "How the OmegaConf inventory backend, an alternative to reclass, handles interpolation, custom resolvers, and the new literal escape syntax."
---

# A Deep Dive into the Kapitan OmegaConf Backend

Reclass has been Kapitan's inventory engine for years. Where it runs out is
small logic inside the inventory: a default value, a condition, a key that
should resolve differently depending on where it is merged. Those cases end
up in Jinja2 or a Kadet helper. The OmegaConf backend handles many of them in
the inventory itself.

The backend is still marked experimental and is not a drop-in replacement
for every reclass inventory. v0.35.1 fixed the part that confused people
most: emitting a literal `${...}` without Kapitan trying to resolve it
([#1445](https://github.com/kapicorp/kapitan/pull/1445)).

<!-- more -->

## Enabling it

The backend ships as an optional extra:

```shell
pip install kapitan[omegaconf]
```

Select it per run:

```shell
kapitan compile --inventory-backend=omegaconf
```

or as the default in `.kapitan`:

```yaml
global:
  inventory-backend: omegaconf
```

## Interpolation

Reclass references use colons, `${path:to:key}`. OmegaConf uses dots:

```yaml
# inventory/targets/my-app.yml
parameters:
  app_name: my-application
  environment: production

  full_name: ${app_name}-${environment}   # "my-application-production"

  config:
    database:
      host: db.example.com
      port: 5432

  db_url: "postgresql://${config.database.host}:${config.database.port}"
  # "postgresql://db.example.com:5432"
```

Defaults use OmegaConf's built-in resolvers:

```yaml
parameters:
  timeout: ${oc.select:custom_timeout, 30}   # 30 unless custom_timeout is set
  log_level: ${oc.env:LOG_LEVEL, INFO}        # read from the environment
```

Kapitan adds conditional and transformation resolvers on top, among them
`if`, `ifelse`, `equal`, `merge`, `dict` and `yaml`. The
[OmegaConf backend docs](../../inventory/omegaconf.md) list all of them.
Logic that used to sit in templates can move into the inventory, next to the
data it works on.

## Deferred evaluation

The backend resolves in two passes. The first resolves normal `${...}`
interpolations and turns anything written as `\${...}` into `${...}`. The
second pass resolves what the first one unescaped. So `\${...}` here means
"resolve later". It does not produce a literal `${` in the output.

Deferring does not change where a resolver such as `parentkey` looks.
`parentkey` returns the key of the node it is written under, and a template
copied by interpolation keeps that key:

```yaml
# inventory/classes/base-deployment.yml
parameters:
  deployment_template:
    name: \${parentkey:}
    namespace: ${namespace}

# inventory/targets/my-app.yml
classes:
  - base-deployment
parameters:
  namespace: production
  deployments:
    web-frontend: ${deployment_template}
    api-backend: "${merge:${deployment_template},{name: api-backend}}"
    worker:
      name: ${parentkey:}
      namespace: ${namespace}
```

`kapitan inventory --inventory-backend omegaconf` shows:

```yaml
deployments:
  api-backend:
    name: api-backend
    namespace: production
  web-frontend:
    name: deployment_template
    namespace: production
  worker:
    name: worker
    namespace: production
```

`web-frontend` gets the template's key. To name an entry after its own key,
write `${parentkey:}` under the entry, as for `worker`, or set `name` while
merging the template, as for `api-backend`. That `merge` value is quoted
because its inline dict contains `: `, which YAML would otherwise read as a
mapping.

## Literal output with `${escape:...}`

Generating Terraform is the common case: the compiled output must contain
`${google_service_account.cluster.email}` as text, for Terraform to resolve.
`\${...}` does not do that, because the second pass still resolves it.

Since #1445, the `escape` resolver covers this. `${escape:content}` emits
`${content}` verbatim and is not touched by either pass:

```yaml
parameters:
  cluster: my-cluster

  terraform_ref: ${escape:google_service_account.cluster.email}
  shell_home: ${escape:HOME}

  # Works mid-string; surrounding interpolations still resolve
  greeting: "Hello ${escape:USER}, welcome to ${cluster}"
```

Compiled output:

```yaml
terraform_ref: ${google_service_account.cluster.email}
shell_home: ${HOME}
greeting: "Hello ${USER}, welcome to my-cluster"
```

The resolver does not return a `${...}` string, which the second pass would
resolve again. It wraps the content in marker strings,
`__KAPITAN_LITERAL__...__KAPITAN_LITERAL_END__`, and a post-processing step
replaces them with `${content}` after both passes have finished. Because of
that, escaped content is safe even when it matches a real inventory key:

```yaml
parameters:
  environment: dev
  escaped_key: ${escape:environment}   # "${environment}", not "dev"
```

To summarise the two: `\${...}` defers resolution to the second pass,
`${escape:...}` never resolves and emits the `${...}` text as is.

For expressions with commas or quotes, such as a Terraform conditional,
quote the argument with single quotes so OmegaConf parses it as one value.
The ` : ` in the conditional also needs the whole YAML value quoted, or the
YAML parser fails with "mapping values are not allowed here":

```yaml
parameters:
  terraform_expression: "${escape:'var.foo == \"bar\" ? 1 : 0'}"
  # ${var.foo == "bar" ? 1 : 0}
```

## Custom resolvers

When the built-in resolvers are not enough, add a `resolvers.py` to the
inventory directory. Resolvers are plain Python functions:

```python
# inventory/resolvers.py

def get_suffix(name: str) -> str:
    """Return the part after the last hyphen."""
    return name.split("-")[-1]

def pass_resolvers():
    return {"get_suffix": get_suffix}
```

```yaml
parameters:
  app_name: my-service
  suffix: ${get_suffix:${app_name}}   # "service"
```

A resolver can also take a `_root_` argument to read the whole inventory,
which is how target-aware lookups such as Vault paths are built. Keep them
small; a resolver with a lot of logic is a template in another place.

## Migrating an existing inventory

`--migrate` rewrites the common reclass patterns in place:

```shell
kapitan compile --inventory-backend=omegaconf --migrate
```

It turns `${path:to:key}` into `${path.to.key}` and `${_reclass_...}` into
`${_kapitan_...}`, and it rewrites every `\${...}` into `${escape:...}`. The
last rewrite cannot tell a reclass literal from a deferred interpolation, so
any `\${parentkey:}`-style entries you rely on for deferred evaluation must
be changed back afterwards. Files containing `!`, `(` or `)` get a different
escape form instead of `${escape:...}`; check those by hand.

Commit the inventory before running `--migrate`, so the rewrite can be
reviewed as a diff and reverted with `git checkout`.

Migration does not cover everything. Keys that contain literal dots need the
`access` resolver, and reclass `exports` and inventory queries are not
supported by the OmegaConf backend.

## When to switch

An inventory that is mostly static data works fine with reclass. The
OmegaConf backend is worth it when you need defaults, conditions, custom
resolvers, or literal `${...}` passed through to Terraform.
Since it is experimental, try it on a branch first, and
[open an issue](https://github.com/kapicorp/kapitan/issues/new/choose) when
something breaks.
