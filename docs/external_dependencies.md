# :kapitan-logo: Fetching external dependencies

Kapitan is capable of fetching components stored in remote locations. This feature can be used by specifying those dependencies in the inventory under `parameters.kapitan.dependencies`. Supported types are:

- [git type](#git-type)
- [http type](#http-type)
- [helm type](#helm-type)

Some use cases of this feature may include:

- using templates/jsonnet libraries hosted remotely
- using values in remote files via `file_read` jsonnet callback

## Usage

```yaml
parameters:
  kapitan:
    dependencies:
    - type: <dependency_type>
      output_path: path/to/file/or/dir
      source: <source_of_dependency>
      # other type-specific parameters, if any
```

Use `--fetch` option to fetch the dependencies:

```shell
kapitan compile --fetch
```

This will download the dependencies and store them at their respective `output_path`.
By default, kapitan does not overwrite existing items with the same name as that of the fetched dependencies.

Use the `--force-fetch` flag to force fetch (update cache with freshly fetched dependencies) and overwrite any existing item sharing the same name in the `output_path`.


```shell
$ kapitan compile --force-fetch
```

Use the `--cache` flag to cache the fetched items in the `.dependency_cache` directory in the root project directory.

```shell
kapitan compile --cache --fetch
```

## Git type

Git types can fetch external dependencies available via HTTP/HTTPS or SSH URLs. This is useful for fetching repositories or their sub-directories, as well as accessing them in specific commits and branches (refs).

**Note**: git types require git binary on your system.

### Usage

```yaml
parameters:
  kapitan:
    dependencies:
    - type: git
      output_path: path/to/dir
      source: git_url
      subdir: relative/path/from/repo/root (optional)
      ref: tag, commit, branch etc. (optional)
```

### Example

Say we want to fetch the source code from our kapitan repository, specifically, `kapicorp/kapitan/kapitan/version.py`. Let's create a very simple target file `inventory/targets/kapitan-example.yml`.

```yaml
parameters:
  kapitan:
    vars:
      target: kapitan-example
    dependencies:
    - type: git
      output_path: source/kapitan
      source: git@github.com:kapicorp/kapitan.git
      subdir: kapitan
      ref: master
    compile:
    - input_paths:
      - source/kapitan/version.py
      input_type: jinja2 # just to copy the file over to target
      output_path: .
```

Then run:

```shell
$ kapitan compile --fetch -t kapitan-example
Dependency git@github.com:kapicorp/kapitan.git : fetching now
Dependency git@github.com:kapicorp/kapitan.git : successfully fetched
Dependency git@github.com:kapicorp/kapitan.git : saved to source/kapitan
Compiled kapitan-example (0.02s)

$ ls source
kapitan
```

This will download the kapitan repository (kapicorp/kapitan), copy the sub-directory `kapitan` and save it to `source/kapitan`. Therefore, `kapicorp/kapitan/kapitan` corresponds to `source/kapitan` locally.

Note that even if you are not using `subdir` parameter, you can and should specify the repository name in the `output_path` parameter. If you only specify `source` as the `output_path`, then all the kapitan files will be under `source` and not `source/kapitan`.

## HTTP type

http[s] types can fetch external dependencies available at `http://` or `https://` URL.

### Usage

```yaml
parameters:
  kapitan:
    dependencies:
    - type: http | https
      output_path: path/to/file
      source: http[s]://<url>
      unpack: True | False
```

`output_path` must fully specify the file name. For example:

```yaml
parameters:
  kapitan:
    dependencies:
    - type: https
      output_path: foo.txt
      source: https://example.com/foo.txt
```

### Example

Say we want to download kapitan README.md file. Since it's on Github, we can access it as <https://raw.githubusercontent.com/kapicorp/kapitan/master/README.md>. Using the following inventory, we can copy this to our target folder:

```yaml
parameters:
  kapitan:
    vars:
      target: kapitan-example
    dependencies:
    - type: https
      output_path: README.md
      source: https://raw.githubusercontent.com/kapicorp/kapitan/master/README.md
    compile:
    - input_paths:
      - README.md
      input_type: jinja2
      output_path: .
```

Then run:

```shell
$ kapitan compile --fetch -t kapitan-example
Dependency https://raw.githubusercontent.com/kapicorp/kapitan/master/README.md : fetching now
Dependency https://raw.githubusercontent.com/kapicorp/kapitan/master/README.md : successfully fetched
Dependency https://raw.githubusercontent.com/kapicorp/kapitan/master/README.md : saved to README.md
Compiled kapitan-example (0.02s)

$ ls
compiled inventory README.md
```

This fetches the README.md file from the URL and save it locally.

Another use case for http types is when we want to download an archive file, such as helm packages, and extract its content.
Setting `unpack: True` will unpack zip or tar files onto the `output_path`. In such cases, set `output_path` to a folder where you extract the content, and not the file name. You can refer to [here](compile.md#example) for the example.

## Helm type

Fetches helm charts and any specific subcharts in the `requirements.yaml` file.

`helm_path` can be used to specify where the `helm` binary name or path.
It defaults to the value of the `KAPITAN_HELM_PATH` environment var or simply to `helm` if neither is set.
You should specify only if you don't want the default behavior.

`source` can be either the URL to a chart repository, or the URL to a chart on an OCI registry (supported since Helm 3.8.0).

### Usage

```yaml
parameters:
  kapitan:
    dependencies:
    - type: helm
      output_path: path/to/chart
      source: http[s]|oci://<helm_chart_repository_url>
      version: <specific chart version>
      chart_name: <name of chart>
      helm_path: <helm binary>
```

### Example

If we want to download the prometheus helm chart we simply add the dependency to the monitoring target.
We want a specific version `11.3.0` so we put that in.

```yaml
parameters:
  kapitan:
    vars:
      target: monitoring
    dependencies:
      - type: helm
        output_path: charts/prometheus
        source: https://kubernetes-charts.storage.googleapis.com
        version: 11.3.0
        chart_name: prometheus
    compile:
      - input_type: helm
        output_path: .
        input_paths:
          - charts/prometheus
        helm_values:
         alertmanager:
            enabled: false
        helm_params:
          namespace: monitoring
          name: prometheus
```

Then run:

```shell
$ kapitan compile --fetch -t monitoring
Dependency helm chart prometheus and version 11.3.0: fetching now
Dependency helm chart prometheus and version 11.3.0: successfully fetched
Dependency helm chart prometheus and version 11.3.0: saved to charts/prometheus
Compiled monitoring (1.48s)

$ tree -L 3
├── charts
│   └── prometheus
│       ├── Chart.yaml
│       ├── README.md
│       ├── charts
│       ├── requirements.lock
│       ├── requirements.yaml
│       ├── templates
│       └── values.yaml
├── compiled
│   ├── monitoring
├── inventory
    ├── classes
        ├── common.yml
        ├── component
```

If you simply want the latest chart available, either don't include the `version` key or specify an empty string.

```yaml
parameters:
  kapitan:
    vars:
      target: monitoring
    dependencies:
      - type: helm
        output_path: charts/prometheus
        source: https://kubernetes-charts.storage.googleapis.com
        version: ""
        chart_name: prometheus
    compile:
      - input_type: helm
        output_path: .
        input_paths:
          - charts/prometheus
        helm_values:
         alertmanager:
            enabled: false
        helm_params:
          namespace: monitoring
          name: prometheus
```

Then run:

```shell
$ kapitan compile --fetch -t monitoring
Dependency helm chart prometheus being fetch with using latest version available
Dependency helm chart prometheus and version : fetching now
Dependency helm chart prometheus and version : successfully fetched
Dependency helm chart prometheus and version : saved to charts/prometheus
Compiled monitoring (1.58s)

$ tree -L 3
├── charts
│   └── prometheus
│       ├── Chart.yaml
│       ├── README.md
│       ├── charts
│       ├── requirements.lock
│       ├── requirements.yaml
│       ├── templates
│       └── values.yaml
├── compiled
│   ├── monitoring
├── inventory
    ├── classes
        ├── common.yml
        ├── component
```
