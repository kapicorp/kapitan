# Overview

The **Inventory** is a core component of Kapitan: this section aims to explain how it works and how to best take advantage of it.

The **Inventory** is a hierarchical `YAML` based structure which you use to capture anything that you want to make available to **Kapitan**, so that it can be passed on to its templating engines.

The first concept to learn about the **Inventory** is the [**target**](#targets). A target is a file, found under the [`inventory/targets`](#targets) substructure, that tells Kapitan what you want to compile. It will usually map to something you want to do with **Kapitan**.

For instance, you might want to define a [**target**](#targets) for each environment that you want to deploy using **Kapitan**.

The **Inventory** lets you also define and reuse common configurations through YAML files that are referred to as [**classes**](#classes): by listing classes into [**target**](#targets), their content gets merged together and allows you to compose complex configurations without repetitions.

By combining [**target**](#targets) and [**classes**](#classes), the **Inventory** becomes the SSOT for your whole configuration, and learning how to use it will unleash the real power of **Kapitan**.

!!! info
    The **Kapitan** **Inventory** is based on an open source project called [reclass](https://github.com/kapicorp/reclass) and you can find the full documentation on our Github clone. However we discourage you to look directly at the reclass documentation before you learn more about **Kapitan**, because **Kapitan** uses a fork of reclass and greatly simplifies the reclass experience.

!!! note
    Kapitan enforces very little structure for the **Inventory**, so that you can adapt it to your specific needs: this might be overwhelming at the beginning: don’t worry, we will explain best practice and give guidelines soon.

By default, Kapitan will search for its **Inventory** under [`inventory/classes`](#classes) and [`inventory/targets`](#targets).

```shell
inventory/
├── classes
│   ├── applications
│   ├── components
│   ├── features
│   ├── kapitan
│   ├── projects
│   └── terraform
└── targets
    ├── examples
    ├── kapicorp
    └── terraform
```
