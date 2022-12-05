# :kapitan-logo: External

This input type executes an external script or binary. This can be used to manipulate already compiled files or
execute binaries outside of kapitan that generate or manipulate files.

For example, [ytt](https://get-ytt.io/) is a useful yaml templating tool. It is not built into the kapitan binary,
however, with the `external` input type, we could specify the `ytt` binary to be executed with specific arguments
and environment variables.

In this example, we're removing a label from a k8s manifests in a directory `ingresses` and placing it into the compiled target directory.

```yaml
parameters:
  target_name: k8s-manifests
  kapitan:
    vars:
      target: ${target_name}
    compile:
      - input_type: external
        input_paths:
          - /usr/local/bin/ytt # path to ytt on system
        output_path: .
        args:
          - -f
          - ingresses/ # directory with ingresses
          - -f
          - ytt/remove.yaml # custom ytt script
          - ">"
          - \${compiled_target_dir}/ingresses/ingresses.yaml # final merged result
```

*Supported output types*: N/A (no need to specify `output_type`)

Additionally, the input type supports field `env_vars`, which can be used to set environment variables for the external command.
By default, the external command doesn't inherit any environment variables from Kapitan's environment.
However, if environment variables `$PATH` or `$HOME` aren't set in `env_vars`, they will be propagated from Kapitan's environment to the external command's environment.

Finally, Kapitan will substitute `${compiled_target_dir}` in both the command's arguments and the environment variables.
This variable needs to be escaped in the configuration to ensure that reclass won't interpret it as a reclass reference.
