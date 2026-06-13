# :kapitan-logo: Environment variables

**Kapitan** reads a small set of `KAPITAN_*` environment variables to tune behaviour
that has no dedicated CLI flag or inventory key. They are all **optional** and fall
back to the defaults listed below.

A few rules apply to every variable on this page:

- They are read from the **process environment only** — there is no inventory
  equivalent for any `KAPITAN_*` variable.
- Each is read during a specific **phase** of a run (fetch, compile, or reveal);
  setting it has no effect outside that phase.
- Export them before invoking `kapitan` (e.g. `KAPITAN_HELM_TIMEOUT=60 kapitan compile`).

## Dependency fetching

Read while fetching external dependencies — `kapitan compile --fetch` or
`--force-fetch`. See [External dependencies](external_dependencies.md).

| Variable | Default | When it applies | Description |
| --- | --- | --- | --- |
| `KAPITAN_FETCH_RETRIES` | `3` | git & http[s] fetch | Maximum attempts per fetch, including the first. Set to `1` to disable retries. |
| `KAPITAN_FETCH_WAIT_MIN` | `0.5` | git & http[s] fetch | Minimum backoff between attempts, in seconds. |
| `KAPITAN_FETCH_WAIT_MAX` | `10` | git & http[s] fetch | Maximum backoff between attempts, in seconds. |
| `KAPITAN_FETCH_TIMEOUT` | `30` | http[s] fetch | Per-request HTTP timeout, in seconds. |

## Helm input

Read when compiling [Helm inputs](input_types/helm.md).

| Variable | Default | When it applies | Description |
| --- | --- | --- | --- |
| `KAPITAN_HELM_PATH` | `helm` | compile (helm input) | Path to the `helm` binary used by the Helm input type. |
| `KAPITAN_HELM_TIMEOUT` | `30` | compile (helm input) | Timeout for helm operations, in seconds. |

## Environment references

The `env` reference backend resolves `?{env:...}` references from the environment at
**reveal** time. See [References](../references.md).

| Variable | Default | When it applies | Description |
| --- | --- | --- | --- |
| `KAPITAN_VAR_<NAME>` | reference default | reveal | Value substituted for the `env` reference `<NAME>`. The lower-case key is tried first, then the upper-cased key; if neither is set, the reference's stored default value is used. |

For example, the reference `?{env:mysql_port}` is revealed from `KAPITAN_VAR_mysql_port`
(or `KAPITAN_VAR_MYSQL_PORT`).
