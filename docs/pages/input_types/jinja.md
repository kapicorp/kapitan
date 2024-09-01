# :kapitan-logo: **Input Type | Jinja2**

This input type is probably the most simple input type to use: it is very versatile and is commonly used to create scripts and documentation files.

It renders [jinja2](http://jinja.palletsprojects.com/en/2.10.x/templates/) templates.


## Example configuration

Here's some configuration from the nginx example

!!! note "examples/kubernetes/inventory/classes/component/nginx-common.yml"

      ```yaml
      --8<-- "kubernetes/inventory/classes/component/nginx-common.yml:4:13"
      ```

      1. We define a list with all the templates we want to compile with this input type
      2. Then input type will render the files a the root of the target compiled folder e.g. `compiled/${target_name}`
      3. We pass the list as `input_paths`

!!! tip ""
      Notice how make use of variable interpolation to use the convenience of a list to add all the files we want to compile.
      You can now simply add to that list from any other place in the inventory that calls that class.

- `input_paths` can either be a file, or a directory: in case of a directory, all the templates in the directory will be rendered.
- `input_params` (optional) can be used to pass extra parameters, helpful when needing to use a similar template for multiple components in the same target.


## Documentation

We usually store documentation templates under the `templates/docs` directory.

!!! example ""
    !!! note "examples/kubernetes/docs/nginx/README.md"
          ```yaml
          --8<-- "kubernetes/docs/nginx/README.md"
          ```

    !!! example "Compiled result"
          ```markdown
          --8<-- "kubernetes/compiled/minikube-nginx-jsonnet/README.md"
          ```

## Scripts

When we use Jinja to render scripts, we tend to call them "canned scripts" to indicate that these scripts have everything needed to run without extra parameters.

We usually store script templates under the `templates/scripts` directory.

!!! example ""
    !!! note "examples/kubernetes/components/nginx-deploy.sh"
          ```shell
          --8<-- "kubernetes/components/nginx-deploy.sh"
          ```

          1. We import the `inventory` as a Jinja variable
          2. We use to set the `namespace` explicitly

    !!! example "Compiled result"
          ```shell hl_lines="5"
          --8<-- "kubernetes/compiled/minikube-nginx-jsonnet/nginx-deploy.sh"
          ```

          1. The script is now a "canned script" and ready to be used for this specif target.
          2. You can see that the namespace has been replaced with the target's one.


## Accessing the inventory

Templates will be provided at runtime with 3 variables:

- `inventory`: To access the inventory for that specific target.
- `inventory_global`: To access the inventory of all targets.
- `input_params`: To access the optional dictionary provided to the input type.

!!! example "Use of `inventory_global`"

    `inventory_global` can be used to generate a "**global**" **`README.md`** that contains a link to all generated targets.
    ```jinja
    | *Target*                                                               |
    |------------------------------------------------------------------------|
    {% for target in inventory_global | sort() %}
    {% set p = inventory_global[target].parameters %}
    |[{{target}}](../{{target}}/docs/README.md)                              |
    {% endfor %}
    ```
    !!! quote "Compiled result"
        ```markdown
        | *Target*                                                               |
        |------------------------------------------------------------------------|
        | [argocd](../argocd/docs/README.md)                                     |
        | [dev-sockshop](../dev-sockshop/docs/README.md)                         |
        | [echo-server](../echo-server/docs/README.md)                           |
        | [examples](../examples/docs/README.md)                                 |
        | [gke-pvm-killer](../gke-pvm-killer/docs/README.md)                     |
        | [global](../global/docs/README.md)                                     |
        | [guestbook-argocd](../guestbook-argocd/docs/README.md)                 |
        | [kapicorp-demo-march](../kapicorp-demo-march/docs/README.md)           |
        | [kapicorp-project-123](../kapicorp-project-123/docs/README.md)         |
        | [kapicorp-terraform-admin](../kapicorp-terraform-admin/docs/README.md) |
        | [mysql](../mysql/docs/README.md)                                       |
        | [postgres-proxy](../postgres-proxy/docs/README.md)                     |
        | [pritunl](../pritunl/docs/README.md)                                   |
        | [prod-sockshop](../prod-sockshop/docs/README.md)                       |
        | [sock-shop](../sock-shop/docs/README.md)                               |
        | [tesoro](../tesoro/docs/README.md)                                     |
        | [tutorial](../tutorial/docs/README.md)                                 |
        | [vault](../vault/docs/README.md)                                       |

        ```

## Jinja2 custom filters

We support the following custom filters for use in Jinja2 templates:

=== "Encoding"
    === "`sha256`"
        !!! example "SHA256 hashing of text"
            `{{ text | sha256 }}`

    === "`yaml`"
        !!! example "Dump text as YAML"
            `{{ text | yaml }}`

    === "`toml`"
        !!! example "Dump text as TOML"
            `{{ text | toml }}`

    === "`b64encode`"
        !!! example "base64 encode text"
            `{{ text | b64encode }}`

    === "`b64decode`"
        !!! example "base64 decode text"
            `{{ text | b64decode }}`

=== "Time"
    === "`to_datetime`"
        !!! example "return datetime object for string"
            `{{ "2019-03-07 13:37:00" | to_datetime }}`
    === "`strftime`"
        !!! example "return current date string for format"
            `{{ "%a, %d %b %Y %H:%M" | strftime }}`

=== "Regexp"
    === "`regex_replace`"
        !!! example "perform a `re.sub` returning a string"
            `{{ hello world | regex_replace(pattern="world", replacement="kapitan")}}`
    === "`regex_escape`"
        !!! example "escape all regular expressions special characters from string"
            `{{ "+s[a-z].*" | regex_escape}}`
    === "`regex_search`"
        !!! example "perform `re.search` and return the list of matches or a backref"
            `{{  hello world | regex_search("world.*")}}`
    === "`regex_findall`"
        !!! example "perform `re.findall` and return the list of matches as array"
            `{{ hello world | regex_findall("world.*")}}`
=== "`fileglob`"
    !!! example "return list of matched regular files for glob"
        `{{ ./path/file* | fileglob }}`
=== "`bool`"
    !!! example "return the bool for value"
        `{{ yes | bool }}`
=== "`ternary`"
    !!! example "`value ? true_val : false_val`"
        `{{ condition | ternary("yes", "no")}}`
=== "`shuffle`"
    !!! example "randomly shuffle elements of a list"
        `{{ [1, 2, 3, 4, 5] | shuffle }}`
=== "`reveal_maybe`"
    !!! example "reveal `ref/secret` tag only if `compile --reveal` flag is set"
        `{{ "?{base64:my_ref}" | reveal_maybe}}`

!!! tip
    You can also provide path to your custom filter modules in CLI. By default, you can put your filters in `lib/jinja2_filters.py` and they will automatically get loaded.
