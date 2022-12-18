# Kubernetes Generator

The Kubernetes generator allows to quickly generate Kubernetes manifests.

## Getting started

### Download the `kapitan-reference` repository

```shell
git clone git@github.com:kapicorp/kapitan-reference.git kapitan-templates
cd kapitan-templates
```

### Create a target file

Create a new kapitan _target_ file in any subdirectory of the `inventory/targets` folder.

For this tutorial, we will assume the target file to be `inventory/targets/demo.yml`

> The target _name_ is the name of the file without the extentions (e.g `demo`).

#### Initial content of `inventory/targets/demo.yml`

```yaml
classes:
  # boilerplate class to get you started
  - common
```

### EVERY CHANGE -> Compile your targets

EVERY time you make a change, you will want to tell `kapitan` to compile your targets.
`kapitan` will create a folder for each target under the `compiled` folder

#### To compile only the `demo` target

`./kapitan compile -t demo`

#### To compile all targets

`./kapitan compile`

## Create a deployment

Let's start by creating a simple component, a `deployment` to be more precise.

> Note: Also see the StatefulSet and Jobs sections!

We will use the `jmalloc/echo-server` for this demo.

The generator is expecting components to be defined under the `parameters.components` path of the inventory.

For instance, create a component `echo-server`, simply create the following section:

```yaml
classes:
  # boilerplate class to get you started
  - common

parameters:
  components:
    echo-server:
      image: jmalloc/echo-server
```

Run `kapitan compile` and check the output in the `compiled/demo/manifests` folder.

## Defining envs

You can define env variables by nesting them under the `env` directive:

```yaml
parameters:
  components:
    echo-server:
      <other config>
      env:
        KAPITAN_ROCKS: 'YES!
```

You can also use `secretKeyRef` and `configMapKeyRef` provided you have defined your secrets/configmaps below.

```yaml
parameters:
  components:
    echo-server:
      <other config>
      env:
        KAPITAN_SECRET:
          secretKeyRef:
            name: a_secret          *OPTIONAL*
            key: 'kapitan_secret'
```

> _NOTE_ that you do not need to specify the `name` directive, as the generator will attempt to work out where to get it from.

Also `fieldRef` works as expected

```yaml
parameters:
  components:
    echo-server:
      <other config>
      env:
        NODE_NAME:
          fieldRef:
            fieldPath: spec.nodeName
```

## Defining ports

You can define the ports your component uses by adding them under the `ports` directive:

```yaml
parameters:
  components:
    echo-server:
      <other config>
      ports:
        http:
          container_port: 8080
```

The above will produce the following effect:

```diff
--- a/compiled/demo/manifests/echo-server-bundle.yml
+++ b/compiled/demo/manifests/echo-server-bundle.yml
@@ -38,6 +38,10 @@ spec:
         - image: jmalloc/echo-server
           imagePullPolicy: IfNotPresent
           name: echo-server
+          ports:
+            - containerPort: 8080
+              name: http
+              protocol: TCP

```

### Liveness and Readiness checks

You can also quickly add a `readiness`/`liveness` check:

```yaml
parameters:
  components:
    echo-server:
      <other config>
      healthcheck:
        readiness:
          type: http
          port: http
          path: /health/readiness
          timeout_seconds: 3
        liveness:
          type: http
          port: http
          path: /health/liveness
          timeout_seconds: 3
```

which produces:

```diff
--- a/compiled/demo/manifests/echo-server-bundle.yml
+++ b/compiled/demo/manifests/echo-server-bundle.yml
@@ -42,6 +42,15 @@ spec:
             - containerPort: 8080
               name: http
               protocol: TCP
+          readinessProbe:
+            failureThreshold: 3
+            httpGet:
+              path: /health/readiness
+              port: http
+              scheme: HTTP
+            periodSeconds: 10
+            successThreshold: 1
+            timeoutSeconds: 3
+          livenessProbe:
+            failureThreshold: 3
+            httpGet:
+              path: /health/liveness
+              port: http
+              scheme: HTTP
+            periodSeconds: 10
+            successThreshold: 1
+            timeoutSeconds: 3
```

> Types `tcp` and `command` are also supported.

## Exposing a service

If you want to expose the service, add the `service` directive with the desired service `type`, and define the `service_port`:

```yaml
parameters:
  components:
    echo-server:
      <other config>
      service:
        type: ClusterIP
      ports:
        http:
          service_port: 80
          container_port: 8080
```

> _Note_: if you want to prevent a port from being added to the service, omit the `<service_port>` directive

Which will create a service manifest with the same name as the component, and will produce the following effect:

```diff
--- a/compiled/demo/manifests/echo-server-bundle.yml
+++ b/compiled/demo/manifests/echo-server-bundle.yml
@@ -52,3 +52,21 @@ metadata:
     name: echo-server
   name: echo-server
   namespace: demo
+---
+apiVersion: v1
+kind: Service
+metadata:
+  labels:
+    app: echo-server
+  name: echo-server
+  namespace: demo
+spec:
+  ports:
+    - name: http
+      port: 80
+      protocol: TCP
+      targetPort: http
+  selector:
+    app: echo-server
+  sessionAffinity: None
+  type: LoadBalancer
```

If you want, you can give the service a different name by using the `service_name` directive.

The service specification uses the following directives:

| directive                 | description                                                              |
| ------------------------- | ------------------------------------------------------------------------ |
| service_name              | \<`string`> defines the name for the service                             |
| type                      | \<`LoadBalancer`\|`ClusterIP`\|`NodePort`> the kubernetes service type   |
| selector                  | \<`dict`> `key`: `value` dict of additional selectors for the service    |
| publish_not_ready_address | \<`bool`> set `spec.publishNotReadyAddresses`                            |
| headless                  | \<`bool`> makes service headless                                         |
| expose_ports              | \<`list[strings]`> list of `component.ports` to expose with this service |
| session_affinity          | \<`ClientIP`\|`None`> sets `spec.sessionAffinity`                        |

## Defining additional services

Sometimes, like in the case of `vault` you might need to define more Services resources than just the main one.
You can then define multiple services with the `additional_services` configuration. Each additional service respect the same options as the main service definition.

```yaml
service:
  service_name: vault-internal
  type: ClusterIP
  publish_not_ready_address: True
  headless: True

additional_services:
  vault-active:
    type: ClusterIP
    publish_not_ready_address: True
    selectors:
      vault-active: "true"
  vault-standby:
    type: ClusterIP
    publish_not_ready_address: True
    selectors:
      vault-active: "false"
```

## Config Maps and Secrets

Creating both `secrets` and `config maps` is very simple with Kapitan Generators, and the interface is very similar with minor differences between them.

### Simple config map

```yaml
config_maps:
  config:
    data:
      echo-service.conf:
        value: |-
          # A configuration file
          example: true
```

A ConfigMap manifest was created. The name is taken from the component.

```yaml
cat compiled/demo/manifests/echo-server-config.yml
apiVersion: v1
data:
  echo-service.conf: '# A configuration file

    example: true'
kind: ConfigMap
metadata:
  labels:
    name: echo-server
  name: echo-server
  namespace: demo
```

## Mounting a config map as a directory

Note that in the previous example the config map is not mounted, because the `mount` directive is missing.

```yaml
config_maps:
  config:
    mount: /opt/echo-service
    data:
      echo-service.conf:
        value: |-
          # A configuration file
          example: true
```

Simply adding the above configuration, will immediately configure the component to mount the config map we have just defined:

```diff
+          volumeMounts:
+            - mountPath: /opt/echo-service
+              name: config
+              readOnly: true
       restartPolicy: Always
       terminationGracePeriodSeconds: 30
+      volumes:
+        - configMap:
+            defaultMode: 420
+            name: echo-server
+          name: config
```

## Use Jinja templates as configurations

A more advanced way to create the configuration file, is to use an external `jinja` file as source:

```yaml
config_maps:
  config:
    mount: /opt/echo-service
    data:
      echo-service.conf:
        template: "components/echo-server/echo-server.conf.j2"
        values:
          example: true
```

with the file [echo-server.conf.j2](../../../components/echo-server/echo-server.conf.j2) being a jinja template file.

As expected, we can inject any value from the inventory into the the file.

### Add external files to ConfigMaps

You can also use the `file` and the `directory` directives to copy a single file or a full directory to your ConfigMaps or Secrets.

```yaml
config_maps:
  config:
    mount: /opt/echo-service
    data:
      example.txt:
        file: "components/echo-server/example.txt"
```

### Filtering files to mount

We do not always expect to mount all files available in a config map. Sometimes in the config map we have a mix of files and other values destined to be consumed by environment variables instead.

For instance, given the following setup, we can restrict the mount only to files defined in the `items` directive:

```yaml
config_maps:
  config:
    mount: /opt/echo-service
    items:
      - echo-service.conf
    data:
      echo-service.conf:
        template: "components/echo-server/echo-server.conf.j2"
        values:
          example: true
      simple_config:
        value: "not mounted"
```

the diff shows that the generator makes use of the items directive in the manifest:

```diff
--- a/compiled/demo/manifests/echo-server-config.yml
+++ b/compiled/demo/manifests/echo-server-bundle.yml
@@ -60,6 +60,9 @@ spec:
       volumes:
         - configMap:
             defaultMode: 420
+            items:
+              - key: echo-service.conf
+                path: echo-service.conf
             name: echo-server
```

### Secrets: auto base64 encode

Secrets use the same configuations as config maps, but are nested under the `secrets` key.

In addition, secrets support automatic base64 encoding with the `b64_encode` directive:

```yaml
secrets:
  secret:
    data:
      encoded_secret:
        value: my_secret
        b64_encode: true
```

```yaml
cat compiled/demo/manifests/echo-server-secret.yml
apiVersion: v1
data:
  encoded_secret: bXlfc2VjcmV0    # ENCODED my_secret
kind: Secret
metadata:
  labels:
    name: echo-server
  name: echo-server
  namespace: demo
type: Opaque

```

> Note that, because in this example the `mount` directive is missing, the secret will not be mounted automatically.

Please review the generic way of Kapitan to manage secrets at [https://kapitan.dev/secrets/](https://kapitan.dev/secrets/) and [Secrets management with Kapitan](https://medium.com/kapitan-blog/secrets-management-with-kapitan-47a0476bab10)

In summary, remember that you can summon the power of Google KMS (once setup) and use kapitan secrets like this:

```yaml
secrets:
  secret:
    data:
      encoded_secret:
        value: my_secret
        b64_encode: true
      better_secret:
        value: ?{gkms:targets/${target_name}/password||randomstr|base64}
```

which will generate an truly encrypted secret using Google KMS (other backends also available)

### Versioned ConfigMaps and Secrets

The generator can automatically "version" you ConfigMap or Secrets so that the associated workload can automatically detect the change and handle it appropriately (rollout restart)

In both secrets and config_maps, just define `versioned: true` (default: `false`)

```yaml
config_maps:
  config:
    versioned: true
    mount: /opt/echo-service
    data:
      example.txt:
        file: "components/echo-server/example.txt"
```

The generator will hash the content of the resource, and add it to the name of the rendered object:

```
kind: ConfigMap
metadata:
  labels:
    name: echo-server
  name: echo-server-01f3716a
  namespace: echo-server
  [cut]
```

when the content of the object changes, the hash will be updated accordingly.

**PLEASE NOTE:** `kapitan` is not responsible for garbage collecting unused secrets of config maps.

### Shared ConfigMaps and Secrets

The generator can create shared Secrets and ConfigMaps.

In secrets, you can define either `string_data` to get a `StringData` secret or `data` to get a `data` secret.
```yaml
parameters:
  generators:
    kubernetes:
      secrets:
        plain-plain-connection:
          string_data:
            CONNECTION:
              value: postgresql://?{plain:targets/${target_name}/shared-password-plain-as-plain-user||randomstr:35}:?{plain:targets/${target_name}/shared-password-plain-as-plain-pass||randomstr:35}/database
```

## Deployment

You can define a _Deployment_ by using the `type` directive to `deployment` (its also the default type)

The deployment uses all (applicable) configurations available to the `deployment` type.

### Volume Mounts and Volumes

**PLEATE NOTE** PV,PVCs are not yet created automatically [Issue #68](https://github.com/kapicorp/kapitan-reference/issues/68)

#### Volume from StorageClass

```yaml
volume_mounts:
  datadir:
    mountPath: /var/lib/mysql

volumes:
  datadir:
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "myStorageClass"
      resources:
        requests:
          storage: 10Gi
```

#### HostPath

```yaml
volume_mounts:
  datadir:
    mountPath: /var/lib/mysql

volumes:
  datadir:
    hostPath:
      path: /mnt/mydisk/mysql
      type: DirectoryOrCreate
```

## DaemonSet

You can define a _DaemonSet_ by using the `type` directive to `daemonset` (its also the default type)

The deployment uses all (applicable) configurations available to the `daemonset` type.

## StatefulSet

You can define a _StatefulSet_ by using the `type` directive to `statefulset` (that normally defaults to `deployment`)

The statefulset uses all (applicable) configurations available to the `deployment` type, but also includes.

### Volume Mounts and Volume Claims

```yaml
volume_mounts:
  datadir:
    mountPath: /var/lib/mysql

volume_claims:
  datadir:
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "standard"
      resources:
        requests:
          storage: 10Gi
```

## Jobs and CronJobs

You can define a _Job_ by using the `type` directive to `job` (that normally defaults to `deployment`)

You can define a _CronJob_ by setting the `schedule` type to a valid value.

```yaml
parameters:
  components:
    postgres-backup:
      type: job
      schedule: "0 */6 * * *"
      image: moep1990/pgbackup:lates
      env:
        PGDATABASE: postgres
        PGHOST: postgres
        PGPASSWORD: postgres
        PGPORT: 5432
        PGUSER: postgres
```

Which will automatically generate the CronJob resource

```yaml
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  labels:
    name: postgres-backup
  name: postgres-backup
spec:
  jobTemplate:
    spec:
      backoffLimit: 1
      completions: 1
      parallelism: 1
      template:
        metadata:
          labels:
            app.kubernetes.io/managed-by: kapitan
            app.kubernetes.io/part-of: gitea
            name: postgres-backup
        spec:
          containers:
            - env:
                - name: PGDATABASE
                  value: postgres
                - name: PGHOST
                  value: postgres
                - name: PGPASSWORD
                  value: postgres
                - name: PGPORT
                  value: "5432"
                - name: PGUSER
                  value: postgres
              image: moep1990/pgbackup:latest
              imagePullPolicy: Always
              name: postgres-backup
          restartPolicy: Never
          terminationGracePeriodSeconds: 30
  schedule: 0 */6 * * *
```

## Additional containers (sidecars)

You can instruct the generator to add one or more additional containers to your definition:

```yaml
parameters:
  components:
    echo-server:
      <other config>
      # Additional containers
      additional_containers:
        nginx:
          image: nginx
          ports:
            nginx:
              service_port: 80
```

You can access the same config_maps and secrets as the main container, but you can override mountpoints and subPaths

For instance while this is defined in the outer "main" container scope, we can still mount the nginx config file:

```yaml
parameters:
  components:
    echo-server:
      <other config>
      # Additional containers
      additional_containers:
        nginx:
          image: nginx
          ports:
            nginx:
              service_port: 80
          config_maps:
            config:
              mount: /etc/nginx/conf.d/nginx.conf
              subPath: nginx.conf

      <other config>
      config_maps:
        config:
          mount: /opt/echo-service/echo-service.conf
          subPath: echo-service.conf
          data:
            echo-service.conf:
              template: "components/echo-server/echo-server.conf.j2"
              values:
                example: true
            nginx.conf:
              value: |
                server {
                   listen       80;
                   server_name  localhost;
                   location / {
                       proxy_pass  http://localhost:8080/;
                   }
                   error_page   500 502 503 504  /50x.html;
                   location = /50x.html {
                       root   /usr/share/nginx/html;
                   }
                }
```

## Init Containers

You can instruct the generator to create initContainers by using the `init_containers` directive:

```yaml
parameters:
  components:
    echo-server:
      <other config>
      # Init containers
      init_containers:
        busybox:
          image: busybox
          commands:
          - echo test
```

Just like the `additional_containers`, tou can access the same config_maps and secrets as the main container, but you can override mountpoints and subPaths.

## Network Policies

You can also generate Network Policies by simply adding them under the `network_policies` structure.

```yaml
# One or many network policies
network_policies:
  default:
    pod_selector:
      name: echo-server
    ingress:
      - from:
          - podSelector:
              matchLabels:
                role: frontend
        ports:
          - protocol: TCP
            port: 6379
```

Which will automatically generate the NetworkPolicy resource

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  labels:
    name: echo-server
  name: echo-server
spec:
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
      ports:
        - port: 6379
          protocol: TCP
  podSelector:
    name: echo-server
  policyTypes:
    - Ingress
    - Egress
```

## Prometheus rules and Service Monitor resources

Define PrometheusRules and ServiceMonitor alongside your application definitions.

For a working example, have a look at [`tesoro_monitoring.yaml`](../../../inventory/classes/components/kapicorp/tesoro_monitoring.yml)

### PrometheusRules

Simply add your definitions:

```yaml
parameters:
  components:
    tesoro:
      prometheus_rules:
        rules:
          - alert: TesoroFailedRequests
            annotations:
              message: "tesoro_requests_failed_total has increased above 0"
            expr: sum by (job, namespace, service, env) (increase(tesoro_requests_failed_total[5m])) > 0
            for: 1m
            labels:
              severity: warning
          - alert: KapitanRevealRequestFailures
            annotations:
              message: "kapitan_reveal_requests_failed_total has increased above 0"
            expr: sum by (job, namespace, service, env) (increase(kapitan_reveal_requests_failed_total[5m])) > 0
            for: 1m
            labels:
              severity: warning
```

to produce:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  labels:
    name: tesoro.rules
  name: tesoro.rules
  namespace: tesoro
spec:
  groups:
    - name: tesoro.rules
      rules:
        - alert: TesoroFailedRequests
          annotations:
            message: tesoro_requests_failed_total has increased above 0
          expr:
            sum by (job, namespace, service, env) (increase(tesoro_requests_failed_total[5m]))
            > 0
          for: 1m
          labels:
            severity: warning
        - alert: KapitanRevealRequestFailures
          annotations:
            message: kapitan_reveal_requests_failed_total has increased above 0
          expr:
            sum by (job, namespace, service, env) (increase(kapitan_reveal_requests_failed_total[5m]))
            > 0
          for: 1m
          labels:
            severity: warning
```

### ServiceMonitor

```yaml
parameters:
  components:
    tesoro:
      service_monitors:
        endpoints:
          - interval: 15s
            path: /
            targetPort: 9095
```

produces the following resource

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  labels:
    name: tesoro-metrics
  name: tesoro-metrics
  namespace: tesoro
spec:
  endpoints:
    - interval: 15s
      path: /
      targetPort: 9095
  jobLabel: tesoro-metrics
  namespaceSelector:
    matchNames:
      - tesoro
  selector:
    matchLabels:
      name: tesoro
```

### Role, Role-Bindings and Cluster-Role, Cluster-Role-Bindings

```yaml
parameters:
  components:
    filebeat:
      # ServiceAccount
      service_account:
        enabled: true
        create: true

      # ROLE + Binding
      role:
        binding:
          subjects:
            - kind: ServiceAccount
          roleRef:
            apiGroup: rbac.authorization.k8s.io
            kind: Role
        rules:
          - apiGroups:
              - ""
            resources:
              - secrets
            verbs:
              - create
              - delete
          - apiGroups:
              - ""
            resources:
              - pods
              - pods/log
            verbs:
              - get
              - create
              - delete
              - list
              - watch
              - update
```

produces the following resource

```yaml
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    name: filebeat
  name: filebeat
  namespace: filebeat
rules:
  - apiGroups:
      - ""
    resources:
      - secrets
    verbs:
      - create
      - delete
  - apiGroups:
      - ""
    resources:
      - pods
      - pods/log
    verbs:
      - get
      - create
      - delete
      - list
      - watch
      - update
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  labels:
    name: filebeat
  name: filebeat
  namespace: filebeat
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: filebeat
subjects:
  - kind: ServiceAccount
    name: filebeat
---
apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    name: filebeat
  name: filebeat
  namespace: filebeat
```

## PodSecurityPolicy

The `spec` is relatively raw here, since its too diverse to be automated enough.
Annotations and labels are merged from global and PSP ones.

```yaml
parameters:
  components:
    drone:
      pod_security_policy:
        annotations:
          xxx: yyy
        labels:
          yyy: zzz
        spec:
          privileged: false
          # Required to prevent escalations to root.
          allowPrivilegeEscalation: false
          # This is redundant with non-root + disallow privilege escalation,
          # but we can provide it for defense in depth.
          requiredDropCapabilities:
            - ALL
          # Allow core volume types.
          volumes:
            - "configMap"
            - "emptyDir"
            - "projected"
            - "secret"
            - "downwardAPI"
            - "persistentVolumeClaim"
          hostNetwork: false
          hostIPC: false
          hostPID: false
          runAsUser:
            rule: "MustRunAsNonRoot"
          seLinux:
            rule: "RunAsAny"
          supplementalGroups:
            rule: "MustRunAs"
            ranges:
              # Forbid adding the root group.
              - min: 1
                max: 65535
          fsGroup:
            rule: "MustRunAs"
            ranges:
              # Forbid adding the root group.
              - min: 1
                max: 65535
          readOnlyRootFilesystem: false
```

produces the following resource

```yaml
---
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  annotations:
    manifests.kapicorp.com/generated: "true"
    xxx: yyy
  labels:
    app.kubernetes.io/component: go
    app.kubernetes.io/managed-by: kapitan
    app.kubernetes.io/part-of: drone
    app.kubernetes.io/version: "1"
    yyy: zzz
  name: drone
  namespace: drone
spec:
  allowPrivilegeEscalation: false
  fsGroup:
    ranges:
      - max: 65535
        min: 1
    rule: MustRunAs
  hostIPC: false
  hostNetwork: false
  hostPID: false
  privileged: false
  readOnlyRootFilesystem: false
  requiredDropCapabilities:
    - ALL
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  supplementalGroups:
    ranges:
      - max: 65535
        min: 1
    rule: MustRunAs
  volumes:
    - configMap
    - emptyDir
    - projected
    - secret
    - downwardAPI
    - persistentVolumeClaim
```

## Defining default values for multiple components

Sometimes, when defining many components, you and up repeating many repeating configurations.
With this generator, you can define defaults in 2 ways:

### Global Generator Defaults

The [global defaults](../../../inventory/classes/kapitan/generators/manifests.yml) can be used to set defaults for every component being generated.

As you can see, some defaults are already set:

```yaml
generators:
  manifest:
    default_config:
      type: deployment
      annotations:
        "manifests.kapicorp.com/generated": true
```

You do not have to change that class directly, as long as you add to the same inventory structure for another class.

For instance, when we enable the [`features.tesoro`](../../../inventory/classes/features/tesoro.yml) class, we can see that we are adding the following yaml fragment:

```yaml
generators:
  manifest:
    default_config:
      globals:
        secrets:
          labels:
            tesoro.kapicorp.com: enabled
```

Which has the effect to add the `tesoro.kapicorp.com: enabled` label to every generated configMap resource.

### Application defaults

You can also create application defaults, where an application is a class/profile that can be associated to multiple components.

For instance, let's assume you have the following definition for an application class called `microservices`

```yaml
parameters:
  applications:
    microservices:
      component_defaults:
        replicas: 3
        env:
          KAPITAN_APPLICATION: microservices
```

Every component that belongs to that application class will receive the defaults for the application.
To associate a component to an application, use the `application` directive.

```yaml
parameters:
  components:
    echo-server:
      application: microservices
      image: jmalloc/echo-server
```

Compiling, kapitan will generate a _deployment_ with image `jmalloc/echo-server`, 3 replicas, an annotation and an env variable.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    manifests.kapicorp.com/generated: "true"
  labels:
    app: echo-server
  name: echo-server
  namespace: tutorial
spec:
  replicas: 3
  selector:
    matchLabels:
      app: echo-server
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
    type: RollingUpdate
  template:
    metadata:
      labels:
        app: echo-server
    spec:
      containers:
        - env:
            - name: KAPITAN_APPLICATION
              value: microservices
          image: jmalloc/echo-server
          imagePullPolicy: IfNotPresent
          name: echo-server
      restartPolicy: Always
      terminationGracePeriodSeconds: 30
```
