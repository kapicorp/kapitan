# :kapitan-logo: **Kapitan Overview**

## Setup your repository

!!! note
    We are currently working on improving the experience to give you an even quicker experience with Kapitan

### Quickstart

[kapicorp/kapitan-reference](https://github.com/kapicorp/kapitan-reference) repository is meant to be a way to bootstrap your **Kapitan** setup to get you up and running.

It is meant to help you make use of best practices and libraries that can make Kapitan the ultimate tool for all your configuration needs.

```
$ git clone git@github.com:kapicorp/kapitan-reference.git kapitan-templates
$ cd kapitan-templates

$ ./kapitan compile
Compiled postgres-proxy (1.51s)
Compiled tesoro (1.70s)
Compiled echo-server (1.64s)
Compiled mysql (1.67s)
Compiled gke-pvm-killer (1.17s)
Compiled prod-sockshop (4.74s)
Compiled dev-sockshop (4.74s)
Compiled tutorial (1.68s)
Compiled global (0.76s)
Compiled examples (2.60s)
Compiled pritunl (2.03s)
Compiled sock-shop (4.36s)
```

### From Scratch (Advanced)

!!! warning

    the `kapitan init` command leaves you with a bare configuration. Setting up Kapitan might require time. 
    
    Please use the [**Quickstart**](#quickstart) setup if you want to get started quicker.

If you want to start off with a clean **kapitan** project, you can run `kapitan init --directory <directory>` to populate a new directory with the recommended kapitan folder structure.

The bare minimum structure that makes use of kapitan features may look as follows:

```text
.
├── components
│   ├── mycomponent.jsonnet
├── templates
├── ├── README.md
├── inventory
│   ├── classes
│   │   ├── common.yml
│   └── targets
│       ├── dev.yml
│       ├── staging.yml
│       └── prod.yml
├── refs
│   ├── targets
│   │   ├── prod
│   │   │   └── password
└───├── common
        └── example-com-tls.key
```

* `components`: template files for kadet, jsonnet and helm
* `templates`: stores Jinja2 templates for scripts and documentation
* `inventory/targets`: target files
* `inventory/classes`: inventory classes to be inherited by targets
* `refs`: references files
