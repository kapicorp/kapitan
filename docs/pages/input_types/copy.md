# :kapitan-logo: Copy

This input type simply copies the input templates to the output directory without any rendering/processing.
For Copy, `input_paths` can be either a file or a directory: in case of a directory, all the templates in the directory will be copied and outputted to `output_path`.

*Supported output types*: N/A (no need to specify `output_type`)

Example

```yaml
 kapitan:
    compile:
      - input_type: copy
        ignore_missing: true  # Do not error if path is missing. Defaults to False
        input_paths:
          - resources/state/${target_name}/.terraform.lock.hcl
        output_path: terraform/
```
