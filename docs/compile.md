# Kapitan compile

**Note:** make sure to read up on [inventory](inventory.md) before moving on.

## Specifying inputs and outputs

Input types can be specified in the inventory under `kapitan.compile` in the following format:

```yaml
parameters:
  kapitan:
    compile:
    - output_path: <output_path_in_target_dir>
      input_type: jinja | jsonnet | kadet | helm
      input_paths:
      	- path/to/input/dir/or/file
      output_type: <output_type_specific_to_input_type>
```

## Supported input types

Kapitan supports the following input template types:

- [jinja](#jinja)
- [jsonnet](#jsonnet)
- [kadet](#kadet) (alpha)
- [helm](#helm) (alpha)


### jinja

This renders jinja2 templates, typically stored in `templates/` directory, such as README, scripts and config files. Refer to [jinja2 docs](http://jinja.palletsprojects.com/en/2.10.x/templates/) to understand how the template engine works.

For Jinja2, `input_paths` can be either a file or a directory: in case of a directory, all the templates in the directory will be rendered and outputted to `output_path`.

*Supported output types*: N/A (no need to specify `output_type`)

#### Using the inventory in jinja2

Jinja2 types will pass the "inventory" and whatever target vars as context keys in your template.

This snippet renders the same java_opts for the elasticsearch data role:

```jinja2
java_opts for elasticsearch data role are: {{ inventory.parameters.elasticsearch.roles.data.java_opts }}
```

#### Jinja2 custom filters

We support the following custom filters for use in Jinja2 templates:

```
sha256 - SHA256 hashing of text e.g. {{ text | sha256 }}
yaml - Dump text as YAML e.g. {{ text | yaml }}
b64encode - base64 encode text e.g. {{ text | b64encode }}
b64decode - base64 decode text e.g. {{ text | b64decode }}
fileglob - return list of matched regular files for glob e.g. {{ ./path/file* | fileglob }}
bool - return the bool for value e.g. {{ yes | bool }}
to_datetime - return datetime object for string e.g. {{ "2019-03-07 13:37:00" | to_datetime }}
strftime - return current date string for format e.g. {{ "%a, %d %b %Y %H:%M" | strftime }}
regex_replace - perform a re.sub returning a string e.g. {{ hello world | regex_replace(pattern="world", replacement="kapitan") }}
regex_escape - escape all regular expressions special characters from string e.g. {{ "+s[a-z].*" | regex_escape }}
regex_search - perform re.search and return the list of matches or a backref e.g. {{ hello world | regex_search("world.*") }}
regex_findall - perform re.findall and return the list of matches as array e.g. {{ hello world | regex_findall("world.*") }}
ternary - value ? true_val : false_val e.g. {{ condition | ternary("yes", "no") }}
shuffle - randomly shuffle elements of a list {{ [1, 2, 3, 4, 5] | shuffle }}
reveal_maybe - reveal ref/secret tag only if `compile --reveal` flag is set e.g. {{ "?{ref:my_ref}" | reveal_maybe }}
```

You can also provide path to your custom filter modules in CLI. By default, you can put your filters in `lib/jinja2_filters.py` and they will automatically get loaded.

### jsonnet

Jsonnet is a superset of json format that includes features such as conditionals, variables and imports. Refer to [jsonnet docs](https://jsonnet.org/learning/tutorial.html) to understand how it works.

Note that unlike jinja2 templates, one jsonnet template can output multiple files (one per object declared in the file).

*Supported output types:*

- yaml (default)
- json

#### Using the inventory in jsonnet

Typical jsonnet files would start as follows:

```
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();
```

The first line is required to access the kapitan inventory values. 

On the second line, `inventory()` callback is used to initialise a local variable through which inventory values for this target can be referenced. For example, the script below

```
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();

{
    "data_java_opts": inventory.parameters.elasticsearch.roles.data.java_opts,
}
```

imports the inventory for the target you're compiling and returns the java_opts for the elasticsearch data role. 

#### Callback functions

In addition, importing `kapitan.libjsonnet` makes available the following native_callback functions gluing reclass to jsonnet (amongst others):

```
yaml_load - returns a json string of the specified yaml file
yaml_load_stream - returns a list of json strings of the specified yaml file
yaml_dump - returns a string yaml from a json string
file_read - reads the file specified
jinja2_template - renders the jinja2 file with context specified
sha256_string - returns sha256 of string
gzip_b64 - returns base64 encoded gzip of obj
inventory - returns a dictionary with the inventory for target
jsonschema - validates obj with schema, returns object with 'valid' and 'reason' keys
```
##### Jsonschema validation from jsonnet

Given the follow example inventory:

```
mysql:
  storage: 10G
  storage_class: standard
  image: mysql:latest
```

The yaml inventory structure can be validated with the new `jsonschema()` function:

```
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

For example, if defining the `storage` value with an invalid pattern (`10Z`), compile fails:

```
Jsonnet error: failed to compile /code/components/mysql/main.jsonnet:
 RUNTIME ERROR: '10Z' does not match '^[0-9]+[MGT]{1}$'

Failed validating 'pattern' in schema['properties']['storage']:
    {'pattern': '^[0-9]+[MGT]{1}$', 'type': 'string'}

On instance['storage']:
    '10Z'

/code/mysql/main.jsonnet:(19:1)-(43:2)

Compile error: failed to compile target: minikube-mysql
```

##### Jinja2 jsonnet templating

The following jsonnet snippet renders the jinja2 template in `templates/got.j2`:

```
local kap = import "lib/kapitan.libjsonnet";

{
    "jon_snow": kap.jinja2_template("templates/got.j2", { is_dead: false }),
}
```

It's up to you to decide what the output is.

### kadet

This input type is experimental. See <https://github.com/deepmind/kapitan/pull/190> for its usage.

*Supported output types:*

- yaml (default)
- json

### helm

This is a Python binding to `helm template` command for users with helm charts. This does not require the helm executable, and the templates are rendered without the Tiller server.

Unlike other input types, Helm input types support the following additional parameters under `kapitan.compile`:

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

- namespace: equivalent of `--namespace` option: note that due to the restriction on `helm template` command, specifying the namespace does not automatically add `metadata.namespace` property to the resources. Therefore, users are encourage to explicitly specify in all resources:

    ```yaml
    metadata:
      namespace: {{ .Release.Namespace }} # or any other custom values
    ```

- name_template: equivalent of `--name-template` option
- release_name: equivalent of `--name` option

See the [helm doc](https://helm.sh/docs/helm/#helm-template) for further detail.

#### Example

Let's use [nginx-ingress](https://github.com/helm/charts/tree/master/stable/nginx-ingress) helm chart as the input. Using [kapitan dependency manager](external_dependencies.md), this chart can be fetched via a URL as listed in <https://helm.nginx.com/stable/index.yaml>. 

*On a side note, `https://helm.nginx.com/stable/` is the chart repository URL which you would `helm repo add`, and this repository should contain `index.yaml` that lists out all the available charts and their URLs. By locating this `index.yaml` file, you can locate all the charts available in the repository.*

We can use version 0.3.3 found at https://helm.nginx.com/stable/nginx-ingress-0.3.3.tgz. We can create a simple target file as `inventory/targets/nginx-from-chart.yml` whose content is as follows:

```yaml
parameters:
  kapitan:
    vars:
      target: nginx-from-chart
    dependencies:
    - type: https
      source: https://helm.nginx.com/stable/nginx-ingress-0.3.3.tgz
      unpack: True
      output_path: components/charts
    compile:
      - output_path: .
        input_type: helm
        input_paths:
          - components/charts/nginx-ingress
        helm_values:
          controller:
            name: my-controller
            image:
              repository: custom_repo
        helm_params:
          release_name: my-first-release-name
          namespace: my-first-namespace
```

To compile this target, run:

```shell
$ kapitan compile --fetch
Dependency https://helm.nginx.com/stable/nginx-ingress-0.3.3.tgz : fetching now
Dependency https://helm.nginx.com/stable/nginx-ingress-0.3.3.tgz : successfully fetched
Dependency https://helm.nginx.com/stable/nginx-ingress-0.3.3.tgz : extracted to components/charts
Compiled nginx-from-chart (0.07s)
```

The chart is fetched before compile, which creates `components/charts/nginx-ingress` folder that is used as the `input_paths`  for the helm input type. To confirm if the `helm_values` actually has overridden the default values, we can try:

```shell
$ grep "my-controller" compiled/nginx-from-chart/nginx-ingress/templates/controller-deployment.yaml 
  name: my-controller
      app: my-controller
        app: my-controller
```

#### Building the binding from source

Run

```shell
cd kapitan/inputs/helm
./build.sh
```

This requires Go >= 1.12.

#### Helm subcharts

This binding supports helm subcharts. However, since the [external dependency manager](external_dependencies.md) does not parse `requirements.yaml` in order to detect chart dependencies, you are required to manually download the entire chart including the parent charts.

*Supported output types:* N/A (no need to specify `output_type`)
