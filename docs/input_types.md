# Input types

Kapitan supports the following input template types:

- [jinja2][#jinja2]
- [jsonnet](#jsonnet)
- [kadet](#kadet) (alpha)
- [helm](#helm) (optional)



THE FOLLOWING CAN PROBABLY BE UNDER STRUCTURE RATHER THAN INPUT TYPES

Input types can be specified in the inventory under `kapitan.compile` in the following format:

```yaml
parameters:
  kapitan:
    compile:
    - output_path: <output_path_in_target_dir>
      input_type: <input_type>
      input_paths:
      	- <path_to_input_file_or_directory>
      output_type: <output_type> 
```



## jinja2

This can render any files with jinja2 template.

For Jinja2, input paths can be either a file or a directory: in case of directory, all the templates in the directory will be rendered and outputted to output_path.

**Supported output types:** N/A (no need to specify this parameter)



## jsonnet

Jsonnet is a superset of json format. Typical jsonnet files as kapitan input would start as follows:

```
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();
```

The first line is required to access the kapitan inventory values. In addition,  importing `kapitan.libjsonnet` makes available the following native_callback functions gluing reclass to jsonnet (amongst others):

```
yaml_load - returns a json string of the specified yaml file
yaml_dump - returns a string yaml from a json string
file_read - reads the file specified
jinja2_render_file - renders the jinja2 file with context specified
sha256_string - returns sha256 of string
gzip_b64 - returns base64 encoded gzip of obj
inventory - returns a dictionary with the inventory for target
```

On the second line, `inventory()` callback is used to initialise a local variable through which inventory values for this target can be referenced. For example, the script below

```
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();

{
    "data_java_opts": inventory.parameters.elasticsearch.roles.data.java_opts,
}
```

imports the inventory for the target you're compiling and returns the java_opts for the elasticsearch data role. 

Note that unlike jinja2 templates, one jsonnet template can output multiple files (one per object declared in the file).

**Supported output types:**

- yaml (default)
- json



## kadet (experimental)

See <https://github.com/deepmind/kapitan/pull/190> for its usage.

**Supported output types:**

- yaml (default)
- json



## helm

This is a binding to `helm template` command for users with helm charts. This input type can be made available by building the binding via `make build_helm_binding`. Unlike any other input types, Helm input types support the following parameters under `kapitan.compile`:

```yaml
parameters:
  kapitan:
    compile:
    - output_path: <output_path>
      input_type: helm
      input_paths:
      	- <chart_path>
      helm_values:
      	<object_with_values_to_override>
      helm_params:
      	namespace: <substitutes_.Release.Namespace>
      	name_template: <namespace_template>
      	release_name: <chart_release_name>
```

`helm_values` is an object containing values specified that will override the default values in the input chart. This has exactly the same effect as specifying `--values custom_values.yml` for `helm template` command where `custom_values.yml` structure mirrors that of `helm_values`. 

`helm_params` correspond to the options for `helm template` as follows:

- namespace: equivalent of `--namespace` option
- name_template: equivalent of `--name-template` option

- release_name: equivalent of `--name` option

See the [helm doc](<https://helm.sh/docs/helm/#helm-template>) for further detail.

**Supported output types**: N/A (no need to specify this parameter)