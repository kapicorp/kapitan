# Parameters Interpolation

!!! note

    as a shorthand, when we encounter deep yaml structures like the following:

    ```yaml
    parameters:
      components:
        nginx:
          image: nginx:latest
    ```

    Usually when we want to talk about the `image` subkey, we normally use either of the following:

      * `parameters.components.nginx.image`
      * `components.nginx.image`

    However, when used in parameter expansion, remember to:

      * replace the `.` with `:`
      * omit the `parameters` initial key which is implied
      * wrap it into the `${}` variable interpolation syntax

    The correct way to reference `parameters.nginx.image` then becomes `${components:nginx:image}`.

The [**Inventory**](introduction.md) allows you to refer to other values defined elsewhere in the structure, using parameter interpolation.

Given the example:

```yaml

parameters:
  cluster:
    location: europe

  application:
    location: ${cluster:location}

  namespace: ${target_name}
  target_name: dev
```



Here we tell **Kapitan** that:

* `namespace` should take the same value defined in `target_name`
* `target_name` should take the literal string `dev`
* `application.location` should take the same value as defined in `cluster.location`

It is important to notice that the inventory can refer to values defined in other classes, as long as they are imported by the target. So for instance with the following example

```yaml

classes:
  - project.production

  parameters:
    application:
      location: ${cluster.location}
```

Here in this case `application.location` refers to a value `location` which has been defined elsewhere, perhaps (but not necessarily) in the `project.production` class.

Also notice that the class name (`project.production`) is not in any ways influencing the name or the structed of the yaml it imports into the file
