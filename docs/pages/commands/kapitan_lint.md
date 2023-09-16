# :kapitan-logo: **CLI Reference** | `kapitan lint`

## `kapitan lint`

Perform a checkup on your inventory or refs.

!!! example ""

    ```shell
    ./kapitan lint
    ```

    ??? example "click to expand output"
        ```shell
        Running yamllint on all inventory files...

        .yamllint not found. Using default values
        File ./inventory/classes/components/echo-server.yml has the following issues:
                95:29: forbidden implicit octal value "0550" (octal-values)
        File ./inventory/classes/terraform/gcp/services.yml has the following issues:
                15:11: duplication of key "enable_compute_service" in mapping (key-duplicates)

        Total yamllint issues found: 2

        Checking for orphan classes in inventory...

        No usage found for the following 6 classes:
        {'components.argoproj.cd.argocd-server-oidc',
        'components.helm.cert-manager-helm',
        'components.rabbitmq-operator.rabbitmq-configuration',
        'components.rabbitmq-operator.rabbitmq-operator',
        'features.gkms-demo',
        'projects.localhost.kubernetes.katacoda'}
        ```
