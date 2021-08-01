# Using Kapitan to generate Terraform configuration

kapitan can be used to generate `*.tf.json` with jsonnet and jinja2.

Running `kapitan compile` in this directory would produce 3 terraform projects named `project1`, `project2`, and `project3`:

```shell
$ docker run -t --rm -v $(pwd):/src:delegated kapicorp/kapitan compile
Compiled project3 (0.14s)
Compiled project2 (0.15s)
Compiled project1 (0.16s)

$ tree compiled
compiled
├── project1
│   ├── scripts
│   │   └── terraform.sh
│   └── terraform
│       ├── dns.tf.json
│       ├── output.tf.json
│       └── provider.tf.json
├── project2
│   ├── scripts
│   │   └── terraform.sh
│   └── terraform
│       ├── kubernetes.tf.json
│       ├── output.tf.json
│       └── provider.tf.json
└── project3
    ├── scripts
    │   └── terraform.sh
    └── terraform
        ├── kubernetes.tf.json
        ├── output.tf.json
        └── provider.tf.json

9 directories, 12 files
```

You can now run `terraform` commands as usual:

```
$ cd compiled/project1/terraform/

$ terraform init
$ terraform plan
$ terraform apply
```
