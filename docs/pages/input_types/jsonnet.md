# :kapitan-logo: **Input Type | Jsonnet**

Jsonnet is a superset of json format that includes features such as conditionals, variables and imports. Refer to [jsonnet docs](https://jsonnet.org/learning/tutorial.html) to understand how it works.

Note: unlike jinja2 templates, one jsonnet template can output multiple files (one per object declared in the file).


## Accessing the inventory

Typical jsonnet files would start as follows:

```python
local kap = import "lib/kapitan.libjsonnet"; #(1)!
local inv = kap.inventory(); #(2)!
local p = inv.parameters; #(3)!

{
    "data_java_opts": p.elasticsearch.roles.data.java_opts, #(4)!
}
```

1. Import the **Kapitan** inventory library.
2. Assign the content of the full inventory for this specific target to the `inv` variable.
3. Assign the content of the `inventory.parameters` to a variable `p` for convenience.
4. Use the `p` variable fo access a specific intentory value


Note: The dictionary keys of the jsonnet object are used as filenames for the generated output files.
If your jsonnet is not a dictionary, but is a valid json(net) object, then the output filename will be the same as the input filename. E.g. `'my_string'` is inside `templates/input_file.jsonnet` so the generated output file will be named `input_file.json` for example and will contain `"my_string"`.


## Jinja2 templating

**Kapitan** allows you to compile a Jinja template from within Jsonnet:

```json
local kap = import "lib/kapitan.libjsonnet";

{
    "jon_snow": kap.jinja2_template("templates/got.j2", { is_dead: false }),
}
```

## Callback functions

In addition, importing `kapitan.libjsonnet` makes available the following native_callback functions gluing reclass to jsonnet (amongst others):

=== "inventory"
    !!! quote ""
        returns a dictionary with the inventory for target
=== "jinja2_template"
    !!! quote ""
        renders the jinja2 file with context specified
=== "yaml"
    === "yaml_load"
        !!! quote ""
            returns a json string of the specified yaml file
    === "yaml_load_stream"
        !!! quote ""
            returns a list of json strings of the specified yaml file
    === "yaml_dump"
        !!! quote ""
            returns a string yaml from a json string
    === "yaml_dump_stream"
        !!! quote ""
            returns a string yaml stream from a json string
=== "file I/O"
    === "file_read"
        !!! quote ""
            reads the file specified
    === "file_exists"
        !!! quote ""
            returns informative object if a file exists
    === "dir_files_list"
        !!! quote ""
            returns a list of file in a dir
    === "dir_files_read"
        !!! quote ""
            returns an object with keys - file_name and values - file contents
=== "sha256_string"
    !!! quote ""
        returns sha256 of string
=== "gzip_b64"
    !!! quote ""
        returns base64 encoded gzip of obj
=== "jsonschema"
    !!! quote ""
        validates obj with schema, returns object with 'valid' and 'reason' keys


## Jsonschema validation

Given the follow example inventory:

```yaml
mysql:
  storage: 10G
  storage_class: standard
  image: mysql:latest
```

The yaml inventory structure can be validated with the new `jsonschema()` function:

```json
local schema = {
    type: "object",
    properties: {
        storage: { type: "string", pattern: "^[0-9]+[MGT]{1}$"},
        image: { type: "string" },
    }
};
// run jsonschema validation
local validation = kap.jsonschema(inv.parameters.mysql, schema);
// assert valid, otherwise error with validation.reason
assert validation.valid: validation.reason;
```

If `validation.valid` is not true, it will then fail compilation and display `validation.reason`.

!!! example "Fails validation because `storage` has an invalid pattern (`10Z`)"

    ```shell
    Jsonnet error: failed to compile /code/components/mysql/main.jsonnet:
    RUNTIME ERROR: '10Z' does not match '^[0-9]+[MGT]{1}$'

    Failed validating 'pattern' in schema['properties']['storage']:
        {'pattern': '^[0-9]+[MGT]{1}$', 'type': 'string'}

    On instance['storage']:
        '10Z'

    /code/mysql/main.jsonnet:(19:1)-(43:2)

    Compile error: failed to compile target: minikube-mysql
    ```
