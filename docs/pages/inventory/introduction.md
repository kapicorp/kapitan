# :kapitan-logo: **What is the inventory?**

The **Inventory** is a core component of Kapitan: this section aims to explain how it works and how to best take advantage of it.

The **Inventory** is a hierarchical `YAML` based structure which you use to capture anything that you want to make available to **Kapitan**, so that it can be passed on to its templating engines.

```
inventory/
├── classes/
│   ├── common/
│   │   └── base.yml        # Foundational configurations
│   ├── components/
│   │   └── web/            # Component-specific settings
│   └── environments/
│       └── production.yml  # Environment-specific configurations
└── targets/
    └── production/
        └── web.yml         # Specific deployment configurations
```

The **Kapitan** inventory is divided between [**targets**](targets.md) and [**classes**](classes.md).

Both classes and targets are yaml file with the same structure

```yaml
classes:
  - common
  - my.other.class

parameters:
  key: value
  key2:
    subkey: value
```

[**Classes**](classes.md) are found by default under the [`inventory/classes`](classes.md) directory and define common settings and data that you define once and can be included in other files. This promotes consistency and reduces duplication.

Classes are identified with a name that maps to the directory structure they are nested under.
In this example, the `kapicorp.common` class represented by the file `classes/kapicorp/common.yml`

```
# classes/kapicorp/common.yml
classes:
  - common

parameters:
  namespace: ${target_name}
  base_docker_repository: quay.io/kapicorp
  base_domain: kapicorp.com
```

[**Targets**](targets.md) are found by default under the [`inventory/targets`](targets.md) directory and represent the different environments or components you want to manage. Each target is a YAML file that defines a set of configurations.

For example, you might have targets for **`production`**, **`staging`**, and **`development`** environments.

```
# targets/production.yml
classes:
  - kapicorp.common
  - components.web
  - environments.production

parameters:
  target_name: web
```


By combining [**target**](targets.md) and [**classes**](classes.md), the **Inventory** becomes the SSOT for your whole configuration, and learning how to use it will unleash the real power of **Kapitan**.
