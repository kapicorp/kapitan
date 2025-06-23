# CUE Lang Input Type

The CUE Lang input type allows you to use [CUE](https://cuelang.org/) to manage, validate, and generate manifests within Kapitan.

## Configuration

The CLUE Lang input type supports the following configuration options:

```yaml
kapitan:
  compile:
    - output_path: cute
      input_type: cuelang
      input_fill_path: "input:" # Optional: the CUE path in which to inject the input value (default at root)
                                # Note: the ':' is not a typo, run `cue help flags` for more information
      yield_path: output # Optional: the CUE field path to yield in the output (default is the whole CUE output)
      input_paths:
        - templates/cue
      input: # Optional: the input value
        some_input: true
```

### Configuration Options

| Option          | Type   | Description                                                                 |
|-----------------|--------|-----------------------------------------------------------------------------|
| `output_path`   | string | Path where compiled manifests will be written                               |
| `input_type`    | string | Must be set to `cuelang` |
| `input_fill_path` | string | Optional: CUE path in which to inject the input value (default at root) |
| `yield_path`    | string | Optional: CUE field path to yield in the output (default is the whole CUE output) |
| `input_paths`   | list  | List of paths to CUE module |
| `input`         | object | Optional: the input value to be used in the CUE templates |

## Examples

### Basic Usage

> Note: You must have a valid CUE module in the specified `input_path`.
> The module takes a numerator and denominator, and calculates the result.

`templates/cue/main.cue`:
```cue
package main

numerator: int
denominator: int & != 0

result: numerator / denominator
```

The following is a valid configuration for the CUE input type:
```yaml
# inventory/targets/cue-example.yaml
parameters:
  kapitan:
    compile:
      - output_path: cute
        input_type: cuelang
        input_paths:
          - templates/cue
        input:
          numerator: 10
          denominator: 2
```

The output will be:
```yaml
# cute/main.yaml
numerator: 10
denominator: 2
result: 5
```

## Troubleshooting

If you encounter issues with the CUE Lang input type, you may try compiling the CUE module manually using the `cue export` command and checking for errors.
You can use the `-l` flag to pass the input value directly to the CUE module:
```bash
cue export templates/cue/main.cue -l input.yaml # put numerator and denominator in input.yaml'
```

## Related

- [CUE Lang Documentation](https://cuelang.org/docs/)
- [Kapitan Input Types](../input_types/introduction.md)
