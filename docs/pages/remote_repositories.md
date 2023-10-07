# :kapitan-logo: Remote Inventories

Kapitan is capable of recursively fetching inventory items stored in remote locations and copy it to the specified output path. This feature can be used by specifying those inventory items in classes or targets under `parameters.kapitan.inventory`. Supported types are:

- [git type](#git-type)
- [http type](#http-type)


Class items can be specified before they are locally available as long as they are fetched in the same run. [Example](#example) of this is given below.

## Git type

Git types can fetch external inventories available via HTTP/HTTPS or SSH URLs. This is useful for fetching repositories or their sub-directories, as well as accessing them in specific commits and branches (refs).

**Note**: git types require git binary on your system.

### Definition

```yaml
parameters:
  kapitan:
    inventory:
    - type: git
      output_path: path/to/dir
      source: git_url
      subdir: relative/path/from/repo/root (optional)
      ref: tag, commit, branch etc. (optional)
```

### Example

Lets say we want to fetch a class from our kapitan repository, specifically
`kapicorp/kapitan/tree/master/examples/docker/inventory/classes/dockerfiles.yml`.

Lets create a simple target file `docker.yml`

!!! example ""

    !!! note

        [external dependencies](external_dependencies.md) are used to fetch dependency items in this example.

    !!! example "`targets/docker.yml`"


        ```yaml
        classes:
          - dockerfiles
        parameters:
          kapitan:
            vars:
              target: docker
            inventory:
              - type: git
                source: https://github.com/kapicorp/kapitan
                subdir: examples/docker/inventory/classes/
                output_path: classes/
            dependencies:
              - type: git
                source: https://github.com/kapicorp/kapitan
                subdir: examples/docker/components
                output_path: components/
              - type: git
                source: https://github.com/kapicorp/kapitan
                subdir: examples/docker/templates
                output_path: templates/
          dockerfiles:
          - name: web
            image: amazoncorretto:11
          - name: worker
            image: amazoncorretto:8
        ```

    !!! example ""

        ```shell
        kapitan compile --fetch
        ```

    ??? example "click to expand output"
        ```shell
        [WARNING] Reclass class not found: 'dockerfiles'. Skipped!
        [WARNING] Reclass class not found: 'dockerfiles'. Skipped!
        Inventory https://github.com/kapicorp/kapitan: fetching now
        Inventory https://github.com/kapicorp/kapitan: successfully fetched
        Inventory https://github.com/kapicorp/kapitan: saved to inventory/classes
        Dependency https://github.com/kapicorp/kapitan: saved to components
        Dependency https://github.com/kapicorp/kapitan: saved to templates
        Compiled docker (0.11s)
        ```



## http type

`http[s]` types can fetch external inventories available at `http://` or `https://` URL.

### Definition

```yaml
parameters:
  kapitan:
    inventory:
    - type: http | https
      output_path: full/path/to/file.yml
      source: http[s]://<url>
      unpack: True | False # False by default
```

### Example

!!! example ""


    !!! example "`targets/mysql-generator-fetch.yml`"


        ```yaml
        classes:
          - common
          - kapitan.generators.kubernetes
        parameters:
          kapitan:
            inventory:
              - type: https
                source: https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml
                output_path: classes/kapitan/generators/kubernetes.yml
          components:
            mysql:
              image: mysql
        ```

    !!! example ""

        ```shell
        kapitan compile --fetch
        ```

    ??? example "click to expand output"
        ```shell
        ./kapitan compile -t mysql-generator-fetch --fetch
        Inventory https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml: fetching now
        Inventory https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml: successfully fetched
        Inventory https://raw.githubusercontent.com/kapicorp/kapitan-reference/master/inventory/classes/kapitan/generators/kubernetes.yml: saved to inventory/classes/kapitan/generators/kubernetes.yml

        ...
        cut
        ...

        Compiled mysql-generator-fetch (0.06s)
        ```
