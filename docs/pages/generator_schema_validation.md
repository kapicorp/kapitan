# Generator schema validation

Generator authors can ship a JSON Schema alongside their generator code so that Kapitan validates the relevant inventory input at compile time. This catches common mistakes (wrong types, missing keys) before rendering starts.

---

## How it works

After fetching a target's dependencies, Kapitan looks for a `schema.json` file next to each dependency's fetched contents. If the file exists, Kapitan validates the inventory subtree defined by `schema_inventory_path` against it.

Findings are emitted as **warnings by default** so existing inventories keep compiling. You can opt into **error** mode for CI or **info** mode for quieter output.

---

## For generator authors

Place a `schema.json` file in the root of the directory you publish. For a Kadet generator the bundle would look like this:

```text
my-generator/
├── __init__.py
├── lib/
│   └── utils.py
└── schema.json
```

The schema is normal [JSON Schema](https://json-schema.org/). A minimal example:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "namespace": {
      "type": "string",
      "minLength": 1
    },
    "syncPolicy": {
      "type": "object",
      "properties": {
        "automated": {
          "type": "boolean"
        }
      }
    }
  }
}
```

Keep reusable definitions inside the same file using `$defs` so consumers only need the single file.

### Generating a schema

You can write the schema by hand or generate it from code:

- **Python / Pydantic** — if your generator already uses Pydantic models for its input, call `Model.model_json_schema()` and save the result as `schema.json`.
- **TypeScript** — use `typescript-json-schema` to emit a schema from an interface or type definition.
- **JSON sample data** — tools such as `genson` or online generators can infer a draft schema from representative inventory YAML/JSON.

Whatever approach you choose, keep the schema in the repository that defines the generator so it is versioned together with the code.

---

## For consumers

### Default discovery

If you do not configure anything extra, Kapitan checks `<output_path>/schema.json` for every dependency:

```yaml
parameters:
  kapitan:
    dependencies:
      - type: git
        source: https://example.com/org/generators.git
        ref: argocd-v1.0.4
        subdir: argocd
        output_path: lib/argocd
```

Kapitan looks for `lib/argocd/schema.json` after fetching.

### Override the schema path

If the schema lives elsewhere, set `schema_path` on the dependency:

```yaml
parameters:
  kapitan:
    dependencies:
      - type: git
        source: https://example.com/org/generators.git
        ref: argocd-v1.0.4
        subdir: argocd
        output_path: lib/argocd
        schema_path: lib/argocd/my/path/schema.json
```

### Define the inventory subtree to validate

By default Kapitan does not know which part of the inventory a schema applies to. Use `schema_inventory_path` to point to the relevant subtree:

```yaml
parameters:
  kapitan:
    dependencies:
      - type: git
        source: https://example.com/org/generators.git
        ref: argocd-v1.0.4
        subdir: argocd
        output_path: lib/argocd
        schema_inventory_path: parameters.components.argocd
```

The path is a dot-separated key path starting from the root of the merged target parameters.

### Validation severity

Control the behaviour per target with `generator_schema_validation`:

```yaml
parameters:
  kapitan:
    generator_schema_validation: warn
```

| Value | Behaviour |
|---|---|
| `warn` (default) | Log findings as warnings; compilation continues. |
| `error` | Collect all violations, then raise `CompileError` on the first dependency that has errors; compilation stops. |
| `info` | Log findings at info level; compilation continues. |
| `disabled` | Skip validation entirely. |

You can set this globally in a shared class or per target.

---

## Discovery rule

For every dependency entry under `parameters.kapitan.dependencies`:

1. Fetch the dependency as Kapitan already does.
2. Determine the candidate schema path:
   - use `schema_path` if set
   - otherwise use `<output_path>/schema.json`
3. If the file does not exist, skip schema validation for that dependency.
4. If the file exists, load it as JSON Schema.
5. Validate the inventory subtree indicated by `schema_inventory_path`.
6. Emit diagnostics according to `generator_schema_validation`.

---

## Example warning

With `generator_schema_validation: warn` and an inventory like:

```yaml
parameters:
  components:
    argocd:
      syncPolicy:
        automated: "true"
```

Kapitan logs:

```text
E-argocd.type

parameters.components.argocd.syncPolicy.automated must satisfy schema constraint
  Problem: 'true' is not of type 'boolean'
  Schema: /home/user/project/lib/argocd/schema.json

inventory/classes/argocd.yml:5:20

  3 |     argocd:
  4 |       syncPolicy:
> 5 |         automated: "true"
  6 |
```

When the source file cannot be found (e.g. the value is computed or inherited without a direct YAML source), Kapitan still prints the error code, key path, problem, and schema path. Source locations are reported only for exact key matches in the inventory YAML files.

---

## Compatibility

- Dependencies without a `schema.json` continue to work unchanged.
- Missing `schema_inventory_path` skips validation for that dependency.
- If `schema_inventory_path` is configured but does not exist in the merged inventory, Kapitan logs a warning so you notice the typo.
- The feature is backward compatible: the default is `warn`, so existing repositories are not broken.
- No generator metadata file or schema directory convention is required.

## Notes

- **Multiple errors** — When a schema has several violations, Kapitan reports every mismatch for that dependency in one pass so you can fix them all at once.
- **Source location caching** — YAML files are parsed once per compile pass and cached, so validation stays fast even for large inventories.
