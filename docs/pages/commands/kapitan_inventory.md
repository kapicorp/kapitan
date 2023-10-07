# :kapitan-logo: **CLI Reference** | `kapitan inventory`

## `kapitan inventory`

Renders the resulting inventory values for a specific target.

For example, rendering the inventory for the `mysql` target:

!!! example ""

    ```shell
    kapitan inventory -t mysql
    ```

    ??? example "click to expand output"
        ```yaml
        __reclass__:
          environment: base
          name: mysql
          node: mysql
          timestamp: Wed Nov 23 23:19:28 2022
          uri: yaml_fs:///src/inventory/targets/examples/mysql.yml
        applications: []
        classes:
          - kapitan.kube
          - kapitan.generators.kubernetes
          - kapitan.generators.argocd
          - kapitan.generators.terraform
          - kapitan.generators.rabbitmq
          - kapitan.common
          - common
          - components.mysql
        environment: base
        exports: {}
        parameters:
          _reclass_:
            environment: base
            name:
              full: mysql
              short: mysql
          components:
            mysql:
              config_maps:
                config:
                  data:
                    mysql.cnf:
                      value: ignore-db-dir=lost+found
                    mytemplate.cnf:
                      template: components/mysql/mytemplate.cnf.j2
                      values:
                        mysql:
                          client:
                            port: 3306
                            socket: /var/run/mysqld/mysqld.sock
                          mysqld:
                            bind-address: 127.0.0.1
                            max_allowed_packet: 64M
                            thread_concurrency: 8
                  mount: /etc/mysql/conf.d/
              env:
                MYSQL_DATABASE: ''
                MYSQL_PASSWORD:
                  secretKeyRef:
                    key: mysql-password
                MYSQL_ROOT_PASSWORD:
                  secretKeyRef:
                    key: mysql-root-password
                MYSQL_USER: ''
              image: mysql:5.7.28
              ports:
                mysql:
                  service_port: 3306
              secrets:
                secrets:
                  data:
                    mysql-password:
                      value: ?{plain:targets/mysql/mysql-password||randomstr|base64}
                    mysql-root-password:
                      value: ?{plain:targets/mysql/mysql-root-password||randomstr:32|base64}
                  versioned: true
              type: statefulset
              volume_claims:
                datadir:
                  spec:
                    accessModes:
                      - ReadWriteOnce
                    resources:
                      requests:
                        storage: 10Gi
                    storageClassName: standard
              volume_mounts:
                datadir:
                  mountPath: /var/lib/mysql
          docs:
            - templates/docs/README.md
          generators:
            manifest:
              default_config:
                annotations:
                  manifests.kapicorp.com/generated: 'true'
                service_account:
                  create: false
                type: deployment
          kapitan:
            compile:
              - input_paths:
                  - components/generators/kubernetes
                input_type: kadet
                output_path: manifests
                output_type: yml
              - input_params:
                  function: generate_docs
                  template_path: templates/docs/service_component.md.j2
                input_paths:
                  - components/generators/kubernetes
                input_type: kadet
                output_path: docs
                output_type: plain
              - input_params:
                  function: generate_pre_deploy
                input_paths:
                  - components/generators/kubernetes
                input_type: kadet
                output_path: pre-deploy
                output_type: yml
              - input_paths:
                  - components/generators/argocd
                input_type: kadet
                output_path: argocd
                output_type: yml
              - input_params:
                  generator_root: resources.tf
                input_paths:
                  - components/generators/terraform
                input_type: kadet
                output_path: terraform
                output_type: json
              - ignore_missing: true
                input_paths:
                  - resources/state/mysql/.terraform.lock.hcl
                input_type: copy
                output_path: terraform/
              - input_paths:
                  - components/generators/rabbitmq
                input_type: kadet
                output_path: rabbitmq
                output_type: yml
              - input_paths:
                  - templates/docs/README.md
                input_type: jinja2
                output_path: docs
              - input_paths: []
                input_type: jinja2
                output_path: scripts
              - input_paths: []
                input_type: jsonnet
                output_path: manifests
                output_type: yml
            dependencies:
              - output_path: lib/kube.libsonnet
                source: https://raw.githubusercontent.com/bitnami-labs/kube-libsonnet/master/kube.libsonnet
                type: https
              - output_path: lib/kube-platforms.libsonnet
                source: https://raw.githubusercontent.com/bitnami-labs/kube-libsonnet/master/kube-platforms.libsonnet
                type: https
              - output_path: components/generators/kubernetes
                ref: master
                source: https://github.com/kapicorp/kapitan-reference.git
                subdir: components/generators/kubernetes
                type: git
              - output_path: components/generators/terraform
                ref: master
                source: https://github.com/kapicorp/kapitan-reference.git
                subdir: components/generators/terraform
                type: git
            vars:
              target: mysql
          manifests: []
          mysql:
            settings:
              client:
                port: 3306
                socket: /var/run/mysqld/mysqld.sock
              mysqld:
                bind-address: 127.0.0.1
                max_allowed_packet: 64M
                thread_concurrency: 8
          namespace: mysql
          scripts: []
          target_name: mysql
        ```
