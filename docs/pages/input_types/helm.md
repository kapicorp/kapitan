# :kapitan-logo: **Input Type | Helm**

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
      helm_values_files:
        - <values_file_path>
      helm_path: <helm binary>
      helm_params:
        name: <chart_release_name>
        namespace: <substitutes_.Release.Namespace>
        output_file: <string>
        validate: true
        …
```

`helm_values` is an object containing values specified that will override the default values in the input chart. This has exactly the same effect as specifying `--values custom_values.yml` for `helm template` command where `custom_values.yml` structure mirrors that of `helm_values`.

`helm_values_files` is an array containing the paths to [helm values files](https://helm.sh/docs/chart_template_guide/values_files/) used as input for the chart. This has exactly the same effect as specifying `--file my_custom_values.yml` for the `helm template` command where `my_custom_values.yml` is a helm values file.
If the same keys exist in `helm_values` and in multiple specified `helm_values_files`, the last indexed file in the `helm_values_files` will take precedence followed by the preceding `helm_values_files` and at the bottom the `helm_values` defined in teh compile block.
There is an example in the tests. The `monitoring-dev`(kapitan/tests/test_resources/inventory/targets/monitoring-dev.yml) and `monitoring-prd`(kapitan/tests/test_resources/inventory/targets/monitoring-prd.yml) targets  both use the `monitoring`(tests/test_resources/inventory/classes/component/monitoring.yml) component.
This component has helm chart input and takes a `common.yml` helm_values file which is "shared" by any target that uses the component and it also takes a dynamically defined file based on a kapitan variable defined in the target.

`helm_path` can be use to provide the helm binary name or path.
`helm_path` defaults to the value of `KAPITAN_HELM_PATH` env var if it is set, else it defaults to `helm`

`helm_params` correspond to the flags for `helm template`. Most flags that helm supports can be used here by replacing '-' by '_' in the flag name.

Flags without argument must have a boolean value, all other flags require a string value.

Special flags:

- `name`: equivalent of helm template `[NAME]` parameter. Ignored if `name_template` is also specified. If neither `name_template` nor `name` are specified, the `--generate-name` flag is used to generate a name.
- `output_file`: name of the single file used to output all the generated resources. This is equivalent to call `helm template` without specifing output dir. If not specified, each resource is generated into a distinct file.

- `include_crds` and `skip_tests`: These flags are enabled by default and should be set to `false` to be removed.
- `debug`: prints the helm debug output in kapitan debug log.
- `namespace`: note that due to the restriction on `helm template` command, specifying the namespace does not automatically add `metadata.namespace` property to the resources. Therefore, users are encouraged to explicitly specify it in all resources:

    ```yaml
    metadata:
      namespace: {{ .Release.Namespace }} # or any other custom values
    ```

See the [helm doc](https://helm.sh/docs/helm/helm_template/) for further detail.

#### Example

Let's use [nginx-ingress](https://github.com/helm/charts/tree/master/stable/nginx-ingress) helm chart as the input. Using [kapitan dependency manager](../external_dependencies.md), this chart can be fetched via a URL as listed in <https://helm.nginx.com/stable/index.yaml>.

*On a side note, `https://helm.nginx.com/stable/` is the chart repository URL which you would `helm repo add`, and this repository should contain `index.yaml` that lists out all the available charts and their URLs. By locating this `index.yaml` file, you can locate all the charts available in the repository.*

We can use version 0.3.3 found at <https://helm.nginx.com/stable/nginx-ingress-0.3.3.tgz>. We can create a simple target file as `inventory/targets/nginx-from-chart.yml` whose content is as follows:

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
          name: my-first-release-name
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

This requires Go 1.14.

#### Helm subcharts

There is an [external dependency manager](../external_dependencies.md) of type `helm` which enables you to specify helm
charts to download, including subcharts.
