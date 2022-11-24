# :kapitan-logo: Commands

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


## `kapitan searchvar`

Shows all inventory files where a variable is declared:

!!! example ""

    ```shell
    ./kapitan searchvar parameters.components.*.image
    ```

    ??? example "click to expand output" 
        ```shell
        ./inventory/classes/components/vault.yml                     ${vault:image}
        ./inventory/classes/components/logstash.yml                  eu.gcr.io/antha-images/logstash:7.5.1
        ./inventory/classes/components/gke-pvm-killer.yml            estafette/estafette-gke-preemptible-killer:1.2.5
        ./inventory/classes/components/mysql.yml                     mysql:5.7.28
        ./inventory/classes/components/postgres-proxy.yml            gcr.io/cloudsql-docker/gce-proxy:1.16
        ./inventory/classes/components/echo-server.yml               jmalloc/echo-server
        ./inventory/classes/components/trivy.yml                     ${trivy:image}
        ./inventory/classes/components/filebeat.yml                  ${filebeat:image}:${filebeat:version}
        ./inventory/classes/components/pritunl/pritunl-mongo.yml     docker.io/bitnami/mongodb:4.2.6-debian-10-r23
        ./inventory/classes/components/pritunl/pritunl.yml           alledm/pritunl
        ./inventory/classes/components/weaveworks/user-db.yml        weaveworksdemos/user-db:0.3.0
        ./inventory/classes/components/weaveworks/catalogue.yml      weaveworksdemos/catalogue:0.3.5
        ./inventory/classes/components/weaveworks/user.yml           weaveworksdemos/user:0.4.7
        ./inventory/classes/components/weaveworks/session-db.yml     redis:alpine
        ./inventory/classes/components/weaveworks/catalogue-db.yml   weaveworksdemos/catalogue-db:0.3.0
        ./inventory/classes/components/weaveworks/carts-db.yml       mongo
        ./inventory/classes/components/weaveworks/orders-db.yml      mongo
        ./inventory/classes/components/weaveworks/orders.yml         weaveworksdemos/orders:0.4.7
        ./inventory/classes/components/weaveworks/shipping.yml       weaveworksdemos/shipping:0.4.8
        ./inventory/classes/components/weaveworks/queue-master.yml   weaveworksdemos/queue-master:0.3.1
        ./inventory/classes/components/weaveworks/rabbitmq.yml       rabbitmq:3.6.8-management
        ./inventory/classes/components/weaveworks/payment.yml        weaveworksdemos/payment:0.4.3
        ./inventory/classes/components/weaveworks/front-end.yml      weaveworksdemos/front-end:0.3.12
        ./inventory/classes/components/weaveworks/carts.yml          weaveworksdemos/carts:0.4.8
        ./inventory/classes/components/kapicorp/tesoro.yml           kapicorp/tesoro
        ```
