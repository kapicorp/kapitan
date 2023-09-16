# :kapitan-logo:  Remove

This input type simply removes files or directories. This can be helpful if you can't control particular files
generated during other compile inputs.

For example, to remove a file named `copy_target`, specify an entry to `input_paths`, `compiled/${kapitan:vars:target}/copy_target`.

```yaml
parameters:
  target_name: removal
  kapitan:
    vars:
      target: ${target_name}
    compile:
      - input_type: copy
        input_paths:
          - copy_target
        output_path: .
      # test removal of a file
      - input_type: remove
        input_paths:
          - compiled/${kapitan:vars:target}/copy_target
        output_path: .
```

As a reminder, each input block within the compile array is run sequentially for a target in Kapitan. If we reversed the order of the inputs above like so:

```yaml
parameters:
  target_name: removal
  kapitan:
    vars:
      target: ${target_name}
    compile:
      - input_type: remove
        input_paths:
          - compiled/${kapitan:vars:target}/copy_target
        output_path: .
      - input_type: copy
        input_paths:
          - copy_target
        output_path: .
```

The first input block would throw an error because the copy input command hasn't run yet to produce the file being removed by the remove input block.

*Supported output types*: N/A (no need to specify `output_type`)
