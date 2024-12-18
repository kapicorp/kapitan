# Advanced Inventory Features

## Target labels

Kapitan allows you to define labels in your inventory, which can then be used to group together targets with similar labels.

For instance you could define the following:

!!! example ""

    Defines a class to add the `customer` label to selected targets

    !!! example "`inventory/classes/type/customer_project.yml`"
        ```yaml
        parameters:
          customer_name: ${target_name} # Defaults to the target_name
          kapitan:
            labels:
              customer: ${customer_name}
        ```

    Apply the class to the target for customer `acme`
    !!! example "`inventory/targets/customers/acme.yml`"

        ```yaml
        classes:
        ...
        - type.customer_project

        parameters:
        ...
        ```

    You can now selectively compile targets for customer `acme` using the following (see see [**Labels**](../commands/kapitan_compile.md#using-labels) for more details )

    !!! example ""

        ```shell
        kapitan compile -l customer=acme
        Compiled acme (0.06s)
        Compiled acme-documentation (0.09s)
        ```
