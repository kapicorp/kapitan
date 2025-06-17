# CUE Lang Input Type

The CUE Lang input type allows you to use [CUE](https://cuelang.org/) to manage, validate, and generate manifests within Kapitan.

## Configuration

The CLUE Lang input type supports the following configuration options:

```yaml
kapitan:
  compile:
    - output_path: cute
      input_type: cuelang
      input_fill_path: "input:"
      yield_path: output
      input_paths:
      - templates/cue
      input:
        some_input: true
```
