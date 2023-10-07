# :kapitan-logo: **CLI Reference** | `kapitan searchvar`

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
