# Using Kapitan to generate Terraform configuration

kapitan can be used to generate `*.tf.json` with jsonnet and jinja2.

Running `kapitan compile` in this directory would produce 3 terraform projects named `project1`, `project2`, and `project3`:

```
$ docker run -t --rm -v $(pwd):/src:delegated deepmind/kapitan compile
Compiled project3 (0.32s)
Compiled project1 (0.39s)
Compiled project2 (0.41s)

$ tree compiled
compiled
├── project1
│   └── manifests
│       ├── dns.tf.json
│       ├── output.tf.json
│       └── provider.tf.json
├── project2
│   └── manifests
│       ├── container.tf.json
│       ├── output.tf.json
│       └── provider.tf.json
└── project3
    └── manifests
        ├── container.tf.json
        ├── output.tf.json
        └── provider.tf.json

6 directories, 9 files
```

You can now run `terraform` commands as usual:

```
$ cd compiled/project1/manifests

$ terraform init
$ terraform plan
$ terraform apply
```
