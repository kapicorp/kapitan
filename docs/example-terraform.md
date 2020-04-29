# Terraform example

We will be looking at how to use Kapitan to compile terraform files with Jsonnet as the input type. It's possible to use other input types, however, Jsonnet is recommended. 
For example, we could use the Kadet input to generate terraform files but this would require templates to be written in YAML then rendered into JSON.
It is possible to allow Kadet to consume JSON as an input. This enables you to integrate your organizations pre-existing terraform JSON file's as templates.
Jsonnet is the most straightforward input type as you will see due to its functional nature. The only appropriate output type is JSON since this is the format that Terraform consumes.

## Directory structure

There are several examples available in `examples/terraform`. This will be our working directory for this documentation. The directory structure is as follows:
```
├── inventory
└── templates
```

It is possible to further extend this locally to include a `lib` directory where a `terraform.libjsonnet` file can be stored for use. This is generally dependent on the project scope and organizational patterns. 
We will describe in more detail the role of each of these folders in the following sections.

### inventory

This folder contains the inventory files used to render the templates for each target. The structure of this folder is as follows:

```
.
├── classes
│   ├── env
│   │   ├── develop.yml
│   │   ├── prod.yml
│   │   └── sandbox.yml
│   ├── provider
│   │   └── gcp.yml
│   └── type
│       └── terraform.yml
├── reclass-config.yml
└── targets
    ├── develop
    │   └── project1.yml
    ├── prod
    │   └── project2.yml
    └── sandbox
        └── project3.yml
```

The `targets` directory enables us to define various projects. We can specify each project as an environment such as `dev`, `staging` and `production` with each having unique parameters.

The following is an example targets file. `type.terraform` is what defines the entry point into the main Jsonnet template file. The parameters in the file `inventory/targets/develop/project1.yml` will then be utilized to set the environmental specific provider/resource configuration.
We define the default region and zone for terraform's provider configuration. The default DNS TTL for the DNS resource is also configured for the development environment.
 
```yaml
classes:
  - type.terraform

parameters:
  name: project1
  region: europe-west2
  zone: europe-west2-a

  dns_default_ttl: 300
```

In the following example, we use a reclass configuration file to specify further parameters that we would like to merge into our project files. Thus we define nodes, which are stored in targets and environmental mandatory parameters stored in `classes/env/`.  The reclass config is shown below:

```yaml
storage_type: yaml_fs
pretty_print: true
output: yaml
inventory_base_uri: .
nodes_uri: targets
classes_uri: classes
compose_node_name: false
class_mappings:
  - develop/*                          env.develop
  - prod/*                             env.prod
  - sandbox/*                          env.sandbox
```
 
The following class `provider.gcp` will be found in all files in this path since it is a common configuration for the cloud authentication module.

```yaml
classes:
  - provider.gcp
```

Further classes that group parameters together can be included. To assist in further refining the configuration. 

### components

We tend to use components as a method to organize Jsonnet files. This is not mandatory since it is possible to configure Kapitan to look for input files wherever you would like.
You can have these in any path just ensure you define that path in `inventory/classes/type/terraform.yml`.

The templates folder is where the Jsonnet is located in this instance as shown below:

```
.
├── cloudbuild.jsonnet
├── dns.jsonnet
├── iam.jsonnet
├── iam_service_account.jsonnet
├── kms.jsonnet
├── kubernetes.jsonnet
├── logging.jsonnet
├── main.jsonnet
├── monitoring.jsonnet
├── org_iam.jsonnet
├── output.jsonnet
├── provider.jsonnet
├── pubsub.jsonnet
├── README.md.j2
└── storage.jsonnet
```

The main thing to understand about terraform components is that they are strictly handled by Jsonnet for simplicity. The rendering logic is as follows:

```json5
{
  "output.tf": output,
  "provider.tf": provider,
  [if name_in_resoures("cloudbuild") then "cloudbuild.tf"]: cloudbuild,
  [if name_in_resoures("container") then "kubernetes.tf"]: kubernetes,
  [if name_in_resoures("dns") then "dns.tf"]: dns,
  [if name_in_resoures("iam") && "serviceaccounts" in p.resources.iam then "iam_service_account.tf"]: iam_service_account,
...
  [if name_in_resoures("pubsub") then "pubsub.tf"]: pubsub,
  [if name_in_resoures("storage") then "storage.tf"]: storage,
}
```

Each Jsonnet file defines a resource and then it is imported. Jsonnet then filters through all the inventory parameters to find specific keys that have been defined. Let's take for example the cloud build resource: 

```json5
local cloudbuild = import "cloudbuild.jsonnet";
...
{
  "output.tf": output,
  "provider.tf": provider,
  [if name_in_resoures("cloudbuild") then "cloudbuild.tf"]: cloudbuild,
...
}
```  

Assuming that one of the configuration files for a specific environment has the parameter key `cloudbuild` set. 
These parameters will then be interpreted by the `cloudbuild.jsonnet` template. 
A file named `cloudbuild.tf.json` will then be compiled using the parameters associated with the `cloudbuild` parameter key. 

It is important to understand that once you have a deeper understanding of Kapitan's capabilities, you can organize these files to a style and logic suitable for your organization.

### templates, docs, scripts

Jinja2 is used to generate documentation that sources information from kapitan's inventory. This enables the ability to have dynamic documentation based on your infrastructure configuration changes.
In `templates/terraform` you will find `README.md.j2`. This is used to generate a `README.md` template to be utilized by terraform's output module.

The following is what generates the documentation:

```json5
  data: {
    template_file: {
      readme: {
        template: kap.jinja2_template("templates/terraform/README.md.j2", inv),
      },
    },
  },

  output: {
    "README.md": {
      value: "${data.template_file.readme.rendered}",
      sensitive: true,
    },
  },
```

The function `kap.jinja2_template()` (imported from `kapitan.libjsonnet`) is used to convert and interpreter the `README.md.j2` file into a raw string using the inventory for evaluation logic.

Based on the various parameters jinja2 decides which sections of the readme should be included. 
When terraform runs it will use the output module to generate your desired `README.md` using information from terraform's state.

Scripts are located in the `scripts` directory. They are compiled using jinja2 as the templating language. An example is as follows:

```shell
export TF_DATA_DIR=$(realpath -m ${DIR}/../../../.TF_DATA_DIR/{{inventory.parameters.name}}) # Folder for TF initialization (preferable outside of compiled)
export OUTPUT_DIR=$(realpath -m ${DIR}/../../../output/{{inventory.parameters.name}}) # Folder for storing output files (preferable outside of compiled)
```

It is good practice to utilize this method to improve integration with various CLI based tools. Scripts help to ensure terraform and
kapitan can function with your CI/CD systems. It generally depends on your organizational workflows. 

### secrets

Although there are no particular secrets in this instance. It is possible to utilize Kapitan secrets as defined in [secrets management](secrets.md).

### Collaboration

In some situations you may find teams that are used to writing terraform in HCL. In such situations it may be difficult to adopt Kapitan into the companies workflows.
We can however use terraform modules to simplify the integration process. This means teams which are used to writing in HCL will not need to completely adopt Jsonnet. 

Modules can be imported into projects by defining them under the `modules` parameter key as shown in `inventory/targets/sandbox`. This means teams will only have to worry about coordinating parameter inputs for different projects.
Jsonnet provides the ability to specify conventions and validation of input parameters. This provides peace of mind to infrastructure administrators around the tools usage.