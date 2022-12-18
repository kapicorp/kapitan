import base64
import hashlib
import os

from kapitan.cached import args
from kapitan.inputs.kadet import BaseObj, CompileError, inventory
from kapitan.utils import render_jinja2_file

from . import k8s

search_paths = args.get("search_paths")

inv = inventory(lazy=True)


def j2(filename, ctx):
    return render_jinja2_file(filename, ctx, search_paths=search_paths)


def merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, value)
            if node is None:
                destination[key] = value
            else:
                merge(value, node)
        else:
            destination[key] = destination.setdefault(key, value)

    return destination


class WorkloadCommon(BaseObj):
    def set_replicas(self, replicas):
        self.root.spec.replicas = replicas

    def add_containers(self, containers):
        self.root.spec.template.spec.setdefault("containers", []).extend(
            [container.root for container in containers]
        )

    def add_init_containers(self, containers):
        self.root.spec.template.spec.setdefault("initContainers", []).extend(
            container.root for container in containers
        )

    def add_volumes(self, volumes):
        for key, value in volumes.items():
            merge({"name": key}, value)
            self.root.spec.template.spec.setdefault("volumes", []).append(value)

    def add_volume_claims(self, volume_claims):
        self.root.spec.setdefault("volumeClaimTemplates", [])
        for key, value in volume_claims.items():
            merge({"metadata": {"name": key, "labels": {"name": key}}}, value)
            self.root.spec.volumeClaimTemplates += [value]

    def add_volumes_for_objects(self, objects):
        for object in objects.root:
            object_name = object.name
            rendered_name = object.root.metadata.name

            if type(object) == ComponentConfig:
                key = "configMap"
                name_key = "name"
            else:
                key = "secret"
                name_key = "secretName"

            template = self.root.spec.template
            if isinstance(self, CronJob):
                template = self.root.spec.jobTemplate.spec.template

            template.spec.setdefault("volumes", []).append(
                {
                    "name": object_name,
                    key: {
                        "defaultMode": object.config.get("default_mode", 420),
                        name_key: rendered_name,
                        "items": [
                            {"key": value, "path": value} for value in object.items
                        ],
                    },
                }
            )


class NetworkPolicy(k8s.Base):
    def new(self):
        self.need("config")
        self.need("workload")
        self.kwargs.apiVersion = "networking.k8s.io/v1"
        self.kwargs.kind = "NetworkPolicy"
        super().new()

    def body(self):
        super().body()
        policy = self.kwargs.config
        workload = self.kwargs.workload
        self.root.spec.podSelector.matchLabels = workload.metadata.labels
        self.root.spec.ingress = policy.ingress
        self.root.spec.egress = policy.egress
        if self.root.spec.ingress:
            self.root.spec.setdefault("policyTypes", []).append("Ingress")

        if self.root.spec.egress:
            self.root.spec.setdefault("policyTypes", []).append("Egress")


class ServiceAccount(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "v1"
        self.kwargs.kind = "ServiceAccount"
        super().new()

    def body(self):
        super().body()
        component = self.kwargs.component
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        self.add_annotations(component.service_account.annotations)
        if component.image_pull_secrets or inv.parameters.pull_secret.name:
            self.root.imagePullSecrets = [
                {
                    "name": component.get(
                        "image_pull_secrets", inv.parameters.pull_secret.name
                    )
                }
            ]


class SharedConfig:
    """Shared class to use for both Secrets and ConfigMaps classes.

    containt anything needed by both classes, so that their behavious is basically the same.
    Each subclass will then implement its own way of adding the data depending on their implementation.
    """

    @staticmethod
    def encode_string(unencoded_string):
        return base64.b64encode(unencoded_string.encode("ascii")).decode("ascii")

    def setup_metadata(self):
        self.add_namespace(
            self.config.get(
                "namespace",
                self.kwargs.component.get("namespace", inv.parameters.namespace),
            )
        )

        self.add_annotations(self.config.annotations)
        self.add_labels(self.config.labels)

        self.items = self.config["items"]
        try:
            if isinstance(self, ConfigMap):
                globals = (
                    inv.parameters.generators.manifest.default_config.globals.config_maps
                )
            else:
                globals = (
                    inv.parameters.generators.manifest.default_config.globals.secrets
                )
            self.add_annotations(globals.get("annotations", {}))
            self.add_labels(globals.get("labels", {}))
        except AttributeError:
            pass

    def add_directory(self, directory, encode=False):
        stringdata = inv.parameters.get("use_tesoro", False)
        if directory and os.path.isdir(directory):
            for filename in os.listdir(directory):
                with open(f"{directory}/{filename}", "r") as f:
                    file_content = f.read()
                    self.add_item(
                        filename,
                        file_content,
                        request_encode=encode,
                        stringdata=stringdata,
                    )

    def add_data(self, data):
        stringdata = inv.parameters.get("use_tesoro", False)

        for key, spec in data.items():
            encode = spec.get("b64_encode", False)

            if "value" in spec:
                value = spec.get("value")
            if "template" in spec:
                value = j2(spec.template, spec.get("values", {}))
            if "file" in spec:
                with open(spec.file, "r") as f:
                    value = f.read()

            self.add_item(key, value, request_encode=encode, stringdata=stringdata)

    def add_string_data(self, string_data, encode=False):
        stringdata = True

        for key, spec in string_data.items():

            if "value" in spec:
                value = spec.get("value")
            if "template" in spec:
                value = j2(spec.template, spec.get("values", {}))
            if "file" in spec:
                with open(spec.file, "r") as f:
                    value = f.read()

            self.add_item(key, value, request_encode=encode, stringdata=stringdata)

    def versioning(self, enabled=False):
        if enabled:
            keys_of_interest = ["data", "binaryData", "stringData"]
            subset = {
                key: value
                for key, value in self.root.to_dict().items()
                if key in keys_of_interest
            }
            self.hash = hashlib.sha256(str(subset).encode()).hexdigest()[:8]
            self.root.metadata.name += f"-{self.hash}"


class ConfigMap(k8s.Base, SharedConfig):
    def new(self):
        self.kwargs.apiVersion = "v1"
        self.kwargs.kind = "ConfigMap"
        super().new()

    def body(self):
        super().body()

    def add_item(self, key, value, request_encode=False, stringdata=False):
        encode = request_encode

        self.root["data"][key] = self.encode_string(value) if encode else value


class ComponentConfig(ConfigMap, SharedConfig):
    def new(self):
        self.need("config")
        super().new()

    def body(self):
        super().body()
        self.config = self.kwargs.config

        self.setup_metadata()
        self.add_data(self.config.data)
        self.add_directory(self.config.directory, encode=False)
        self.versioning(self.config.get("versioned", False))


class Secret(k8s.Base):
    def new(self):
        self.kwargs.apiVersion = "v1"
        self.kwargs.kind = "Secret"
        super().new()

    def body(self):
        super().body()

    def add_item(self, key, value, request_encode=False, stringdata=False):
        encode = not stringdata and request_encode
        field = "stringData" if stringdata else "data"
        self.root[field][key] = self.encode_string(value) if encode else value


class ComponentSecret(Secret, SharedConfig):
    def new(self):
        self.need("config")
        super().new()

    def body(self):
        super().body()
        self.config = self.kwargs.config
        self.root.type = self.config.get("type", "Opaque")

        self.setup_metadata()
        if self.config.data:
            self.add_data(self.config.data)
        if self.config.string_data:
            self.add_string_data(self.config.string_data)
        self.add_directory(self.config.directory, encode=True)
        self.versioning(self.config.get("versioned", False))


class Service(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.need("service_spec")
        self.kwargs.apiVersion = "v1"
        self.kwargs.kind = "Service"
        super().new()

    def body(self):
        component = self.kwargs.component
        workload = self.kwargs.workload
        service_spec = self.kwargs.service_spec

        self.kwargs.name = service_spec.get("service_name", self.kwargs.name)
        super().body()
        self.add_namespace(component.get("namespace", inv.parameters.namespace))

        self.add_labels(component.get("labels", {}))
        self.add_annotations(service_spec.annotations)
        self.root.spec.setdefault("selector", {}).update(
            workload.spec.template.metadata.labels
        )
        self.root.spec.setdefault("selector", {}).update(service_spec.selectors)
        self.root.spec.type = service_spec.type
        if service_spec.get("publish_not_ready_address", False):
            self.root.spec.publishNotReadyAddresses = True
        if service_spec.get("headless", False):
            self.root.spec.clusterIP = "None"
        self.root.spec.clusterIP
        self.root.spec.sessionAffinity = service_spec.get("session_affinity", "None")
        all_ports = [component.ports] + [
            container.ports
            for container in component.additional_containers.values()
            if "ports" in container
        ]

        exposed_ports = {}

        for port in all_ports:
            for port_name in port.keys():
                if (
                    not service_spec.expose_ports
                    or port_name in service_spec.expose_ports
                ):
                    exposed_ports.update(port)

        for port_name in sorted(exposed_ports):
            self.root.spec.setdefault("ports", [])
            port_spec = exposed_ports[port_name]
            if "service_port" in port_spec:
                self.root.spec.setdefault("ports", []).append(
                    {
                        "name": port_name,
                        "port": port_spec.service_port,
                        "targetPort": port_name,
                        "protocol": port_spec.get("protocol", "TCP"),
                    }
                )


class Ingress(k8s.Base):
    def new(self):
        self.need("name")
        self.need("ingress")
        self.kwargs.apiVersion = "networking.k8s.io/v1"
        self.kwargs.kind = "Ingress"
        super().new()

    def body(self):
        super().body()
        ingress = self.kwargs.ingress
        self.add_namespace(ingress.get("namespace", inv.parameters.namespace))
        import json

        self.add_annotations(ingress.get("annotations", {}))
        self.add_labels(ingress.get("labels", {}))
        if "default_backend" in ingress:
            self.root.spec.backend.service.name = ingress.default_backend.get("name")
            self.root.spec.backend.service.port = ingress.default_backend.get(
                "port", 80
            )
        if "paths" in ingress:
            host = ingress.host
            paths = ingress.paths
            self.root.spec.rules = [{"host": host, "http": {"paths": paths}}]
        if ingress.tls:
            self.root.spec.tls = ingress.tls


class ManagedCertificate(k8s.Base):
    def new(self):
        self.need("name")
        self.need("domains")
        self.kwargs.apiVersion = "networking.gke.io/v1beta1"
        self.kwargs.kind = "ManagedCertificate"
        super().new()

    def body(self):
        super().body()
        name = self.kwargs.name
        domains = self.kwargs.domains
        self.add_namespace(inv.parameters.namespace)
        self.root.spec.domains = domains


class CertManagerIssuer(k8s.Base):
    def new(self):
        self.need("config_spec")
        self.kwargs.apiVersion = "cert-manager.io/v1"
        self.kwargs.kind = "Issuer"
        super().new()

    def body(self):
        config_spec = self.kwargs.config_spec
        self.add_namespace(config_spec.get("namespace", inv.parameters.namespace))
        super().body()
        self.root.spec = config_spec.get("spec")


class CertManagerClusterIssuer(k8s.Base):
    def new(self):
        self.need("config_spec")
        self.kwargs.apiVersion = "cert-manager.io/v1"
        self.kwargs.kind = "ClusterIssuer"
        super().new()

    def body(self):
        super().body()
        config_spec = self.kwargs.config_spec
        self.root.spec = config_spec.get("spec")


class CertManagerCertificate(k8s.Base):
    def new(self):
        self.need("config_spec")
        self.kwargs.apiVersion = "cert-manager.io/v1"
        self.kwargs.kind = "Certificate"
        super().new()

    def body(self):
        config_spec = self.kwargs.config_spec
        self.add_namespace(config_spec.get("namespace", inv.parameters.namespace))
        super().body()
        self.root.spec = config_spec.get("spec")


class IstioPolicy(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.kwargs.apiVersion = "authentication.istio.io/v1alpha1"
        self.kwargs.kind = "Policy"
        super().new()

    def body(self):
        config_spec = self.kwargs.config_spec
        self.add_namespace(config_spec.get("namespace", inv.parameters.namespace))
        super().body()
        component = self.kwargs.component
        name = self.kwargs.name
        self.root.spec.origins = component.istio_policy.policies.origins
        self.root.spec.principalBinding = "USE_ORIGIN"
        self.root.spec.targets = [{"name": name}]


class NameSpace(k8s.Base):
    def new(self):
        self.need("name")
        self.kwargs.apiVersion = "v1"
        self.kwargs.kind = "Namespace"
        super().new()

    def body(self):
        super().body()
        name = self.kwargs.name
        labels = inv.parameters.generators.kubernetes.namespace.labels
        annotations = inv.parameters.generators.kubernetes.namespace.annotations
        self.add_labels(labels)
        self.add_annotations(annotations)


class Deployment(k8s.Base, WorkloadCommon):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "apps/v1"
        self.kwargs.kind = "Deployment"
        super().new()

    def body(self):
        default_strategy = {
            "type": "RollingUpdate",
            "rollingUpdate": {"maxSurge": "25%", "maxUnavailable": "25%"},
        }
        super().body()
        component = self.kwargs.component
        self.root.spec.template.metadata.setdefault("labels", {}).update(
            component.labels + self.root.metadata.labels
        )
        self.root.spec.selector.setdefault("matchLabels", {}).update(
            component.labels + self.root.metadata.labels
        )
        self.root.spec.template.spec.restartPolicy = component.get(
            "restart_policy", "Always"
        )
        if "host_network" in component:
            self.root.spec.template.spec.hostNetwork = component.host_network
        if "host_pid" in component:
            self.root.spec.template.spec.hostPID = component.host_pid
        self.root.spec.strategy = component.get("update_strategy", default_strategy)
        self.root.spec.revisionHistoryLimit = component.revision_history_limit
        self.root.spec.progressDeadlineSeconds = (
            component.deployment_progress_deadline_seconds
        )
        self.set_replicas(component.get("replicas", 1))


class StatefulSet(k8s.Base, WorkloadCommon):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "apps/v1"
        self.kwargs.kind = "StatefulSet"
        super().new()

    def body(self):
        default_strategy = {}
        update_strategy = {"rollingUpdate": {"partition": 0}, "type": "RollingUpdate"}

        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.root.spec.template.metadata.setdefault("labels", {}).update(
            component.labels + self.root.metadata.labels
        )
        self.root.spec.selector.setdefault("matchLabels", {}).update(
            component.labels + self.root.metadata.labels
        )
        self.root.spec.template.spec.restartPolicy = component.get(
            "restart_policy", "Always"
        )
        if "host_network" in component:
            self.root.spec.template.spec.hostNetwork = component.host_network
        if "host_pid" in component:
            self.root.spec.template.spec.hostPID = component.host_pid
        self.root.spec.revisionHistoryLimit = component.revision_history_limit
        self.root.spec.strategy = component.get("strategy", default_strategy)
        self.root.spec.updateStrategy = component.get(
            "update_strategy", update_strategy
        )
        self.root.spec.serviceName = component.service.get("service_name", name)
        self.set_replicas(component.get("replicas", 1))


class DaemonSet(k8s.Base, WorkloadCommon):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "apps/v1"
        self.kwargs.kind = "DaemonSet"
        super().new()

    def body(self):
        default_strategy = {
            "type": "RollingUpdate",
            "rollingUpdate": {"maxSurge": "25%", "maxUnavailable": "25%"},
        }
        super().body()
        component = self.kwargs.component
        self.root.spec.template.metadata.setdefault("labels", {}).update(
            component.labels + self.root.metadata.labels
        )
        self.root.spec.selector.setdefault("matchLabels", {}).update(
            component.labels + self.root.metadata.labels
        )
        self.root.spec.template.spec.restartPolicy = component.get(
            "restart_policy", "Always"
        )
        if "host_network" in component:
            self.root.spec.template.spec.hostNetwork = component.host_network
        if "host_pid" in component:
            self.root.spec.template.spec.hostPID = component.host_pid
        self.root.spec.revisionHistoryLimit = component.revision_history_limit
        self.root.spec.progressDeadlineSeconds = (
            component.deployment_progress_deadline_seconds
        )


class Job(k8s.Base, WorkloadCommon):
    def new(self):
        self.kwargs.apiVersion = "batch/v1"
        self.kwargs.kind = "Job"
        super().new()
        self.need("component")

    def body(self):
        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.root.spec.template.metadata.setdefault("labels", {}).update(
            component.labels + self.root.metadata.labels
        )
        self.root.spec.template.spec.restartPolicy = component.get(
            "restart_policy", "Never"
        )
        if "host_network" in component:
            self.root.spec.template.spec.hostNetwork = component.host_network
        if "host_pid" in component:
            self.root.spec.template.spec.hostPID = component.host_pid
        self.root.spec.backoffLimit = component.get("backoff_limit", 1)
        self.root.spec.completions = component.get("completions", 1)
        self.root.spec.parallelism = component.get("parallelism", 1)


class CronJob(k8s.Base, WorkloadCommon):
    def new(self):
        self.need("component")
        self.need("job")
        self.kwargs.apiVersion = "batch/v1beta1"
        self.kwargs.kind = "CronJob"
        super().new()

    def body(self):
        super().body()
        component = self.kwargs.component
        job = self.kwargs.job
        self.root.metadata = job.root.metadata
        self.root.spec.jobTemplate.spec = job.root.spec
        self.root.spec.schedule = component.schedule


class Container(BaseObj):
    def new(self):
        self.need("name")
        self.need("container")

    @staticmethod
    def find_key_in_config(key, configs):
        for name, config in configs.items():
            if key in config.data.keys():
                return name
        raise (
            BaseException(
                "Unable to find key {} in your configs definitions".format(key)
            )
        )

    def process_envs(self, container):
        for name, value in sorted(container.env.items()):
            if isinstance(value, dict):
                if "fieldRef" in value:
                    self.root.setdefault("env", []).append(
                        {"name": name, "valueFrom": value}
                    )
                elif "secretKeyRef" in value:
                    if "name" not in value["secretKeyRef"]:
                        config_name = self.find_key_in_config(
                            value["secretKeyRef"]["key"], container.secrets
                        )
                        # TODO(ademaria) I keep repeating this logic. Refactor.
                        if len(container.secrets.keys()) == 1:
                            value["secretKeyRef"]["name"] = self.kwargs.name
                        else:
                            value["secretKeyRef"]["name"] = "{}-{}".format(
                                self.kwargs.name, config_name
                            )

                    self.root.setdefault("env", []).append(
                        {"name": name, "valueFrom": value}
                    )
                if "configMapKeyRef" in value:
                    if "name" not in value["configMapKeyRef"]:
                        config_name = self.find_key_in_config(
                            value["configMapKeyRef"]["key"], container.config_maps
                        )
                        # TODO(ademaria) I keep repeating this logic. Refactor.
                        if len(container.config_maps.keys()) == 1:
                            value["configMapKeyRef"]["name"] = self.kwargs.name
                        else:
                            value["configMapKeyRef"]["name"] = "{}-{}".format(
                                self.kwargs.name, config_name
                            )

                    self.root.setdefault("env", []).append(
                        {"name": name, "valueFrom": value}
                    )
            else:
                self.root.setdefault("env", []).append(
                    {"name": name, "value": str(value)}
                )

    def add_volume_mounts_from_configs(self):
        name = self.kwargs.name
        container = self.kwargs.container
        configs = container.config_maps.items()
        secrets = container.secrets.items()
        for object_name, spec in configs:
            if spec is None:
                raise CompileError(
                    f"error with '{object_name}' for component {name}: configuration cannot be empty!"
                )

            if "mount" in spec:
                self.root.setdefault("volumeMounts", [])
                self.root.volumeMounts += [
                    {
                        "mountPath": spec.mount,
                        "readOnly": spec.get("readOnly", None),
                        "name": object_name,
                        "subPath": spec.subPath,
                    }
                ]
        for object_name, spec in secrets:
            if spec is None:
                raise CompileError(
                    f"error with '{object_name}' for component {name}: configuration cannot be empty!"
                )

            if "mount" in spec:
                self.root.setdefault("volumeMounts", []).append(
                    {
                        "mountPath": spec.mount,
                        "readOnly": spec.get("readOnly", None),
                        "name": object_name,
                        "subPath": spec.subPath,
                    }
                )

    def add_volume_mounts(self, volume_mounts):
        for key, value in volume_mounts.items():
            merge({"name": key}, value)
            self.root.setdefault("volumeMounts", []).append(value)

    @staticmethod
    def create_probe(probe_definition):
        probe = BaseObj()
        if "type" in probe_definition:
            probe.root.initialDelaySeconds = probe_definition.get(
                "initial_delay_seconds", 0
            )
            probe.root.periodSeconds = probe_definition.get("period_seconds", 10)
            probe.root.timeoutSeconds = probe_definition.get("timeout_seconds", 5)
            probe.root.successThreshold = probe_definition.get("success_threshold", 1)
            probe.root.failureThreshold = probe_definition.get("failure_threshold", 3)

            if probe_definition.type == "http":
                probe.root.httpGet.scheme = probe_definition.get("scheme", "HTTP")
                probe.root.httpGet.port = probe_definition.get("port", 80)
                probe.root.httpGet.path = probe_definition.path
                probe.root.httpGet.httpHeaders = probe_definition.httpHeaders
            if probe_definition.type == "tcp":
                probe.root.tcpSocket.port = probe_definition.port
            if probe_definition.type == "command":
                probe.root.exec.command = probe_definition.command
        return probe.root

    def body(self):
        name = self.kwargs.name
        container = self.kwargs.container

        self.root.name = name
        self.root.image = container.image
        self.root.imagePullPolicy = container.get("pull_policy", "IfNotPresent")
        if container.lifecycle:
            self.root.lifecycle = container.lifecycle
        self.root.resources = container.resources
        self.root.args = container.args
        self.root.command = container.command
        # legacy container.security
        if container.security:
            self.root.securityContext.allowPrivilegeEscalation = (
                container.security.allow_privilege_escalation
            )
            self.root.securityContext.runAsUser = container.security.user_id
        else:
            self.root.securityContext = container.security_context
        self.add_volume_mounts_from_configs()
        self.add_volume_mounts(container.volume_mounts)

        for name, port in sorted(container.ports.items()):
            self.root.setdefault("ports", [])
            self.root.ports.append(
                {
                    "containerPort": port.get("container_port", port.service_port),
                    "name": name,
                    "protocol": port.get("protocol", "TCP"),
                }
            )

        self.root.startupProbe = self.create_probe(container.healthcheck.startup)
        self.root.livenessProbe = self.create_probe(container.healthcheck.liveness)
        self.root.readinessProbe = self.create_probe(container.healthcheck.readiness)
        self.process_envs(container)


class Workload(WorkloadCommon):
    def new(self):
        self.need("name")
        self.need("component")

    def body(self):
        component = self.kwargs.component
        name = self.kwargs.name
        if component.type == "deployment":
            workload = Deployment(name=name, component=self.kwargs.component)
        elif component.type == "statefulset":
            workload = StatefulSet(name=name, component=self.kwargs.component)
        elif component.type == "daemonset":
            workload = DaemonSet(name=name, component=self.kwargs.component)
        elif component.type == "job":
            workload = Job(name=name, component=self.kwargs.component)
        else:
            raise ()

        if component.get("namespace") or inv.parameters.get("namespace"):
            workload.root.metadata.namespace = component.setdefault(
                "namespace", inv.parameters.namespace
            )
        workload.add_annotations(component.setdefault("annotations", {}))
        workload.root.spec.template.metadata.annotations = component.get(
            "pod_annotations", {}
        )
        workload.add_labels(component.setdefault("labels", {}))
        workload.add_volumes(component.setdefault("volumes", {}))
        workload.add_volume_claims(component.setdefault("volume_claims", {}))
        workload.root.spec.template.spec.securityContext = (
            component.workload_security_context
        )
        workload.root.spec.minReadySeconds = component.min_ready_seconds
        if component.service_account.enabled:
            workload.root.spec.template.spec.serviceAccountName = (
                component.service_account.get("name", name)
            )

        container = Container(name=name, container=component)
        additional_containers = [
            Container(name=name, container=component)
            for name, component in component.additional_containers.items()
        ]
        workload.add_containers([container])
        workload.add_containers(additional_containers)
        init_containers = [
            Container(name=name, container=component)
            for name, component in component.init_containers.items()
        ]

        workload.add_init_containers(init_containers)
        if component.image_pull_secrets or inv.parameters.image_pull_secrets:
            workload.root.spec.template.spec.imagePullSecrets = component.get(
                "image_pull_secrets", inv.parameters.image_pull_secrets
            )
        workload.root.spec.template.spec.dnsPolicy = component.dns_policy
        workload.root.spec.template.spec.terminationGracePeriodSeconds = component.get(
            "grace_period", 30
        )

        if component.node_selector:
            workload.root.spec.template.spec.nodeSelector = component.node_selector

        if component.tolerations:
            workload.root.spec.template.spec.tolerations = component.tolerations

        affinity = workload.root.spec.template.spec.affinity
        if (
            component.prefer_pods_in_node_with_expression
            and not component.node_selector
        ):
            affinity.nodeAffinity.setdefault(
                "preferredDuringSchedulingIgnoredDuringExecutio", []
            )
            affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution.append(
                {
                    "preference": {
                        "matchExpressions": [
                            component.prefer_pods_in_node_with_expression
                        ]
                    },
                    "weight": 1,
                }
            )

        if component.prefer_pods_in_different_nodes:
            affinity.podAntiAffinity.setdefault(
                "preferredDuringSchedulingIgnoredDuringExecution", []
            )
            affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution.append(
                {
                    "podAffinityTerm": {
                        "labelSelector": {
                            "matchExpressions": [
                                {"key": "app", "operator": "In", "values": [name]}
                            ]
                        },
                        "topologyKey": "kubernetes.io/hostname",
                    },
                    "weight": 1,
                }
            )

        if component.prefer_pods_in_different_zones:
            affinity.podAntiAffinity.setdefault(
                "preferredDuringSchedulingIgnoredDuringExecution", []
            )
            affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution.append(
                {
                    "podAffinityTerm": {
                        "labelSelector": {
                            "matchExpressions": [
                                {"key": "app", "operator": "In", "values": [name]}
                            ]
                        },
                        "topologyKey": "failure-domain.beta.kubernetes.io/zone",
                    },
                    "weight": 1,
                }
            )

        self.root = workload.root


class GenerateMultipleObjectsForClass(BaseObj):
    """Helper to generate multiple classes

    As a convention for generators we have that if you define only one policy/config/secret configuration
    for your component, then the name of that resource will be the component {name} itself.

    However if there are multiple objects being defined, then we call them: {name}-{object_name}

    This class helps achieve that for policies/config/secrets to avoid duplication.
    """

    def new(self):
        self.need("name")
        self.need("component")
        self.need("objects")
        self.need("generating_class")
        self.need("workload")
        self.root = []

    def body(self):
        objects = self.kwargs.objects
        name = self.kwargs.name
        component = self.kwargs.component
        generating_class = self.kwargs.generating_class
        workload = self.kwargs.workload

        for object_name, object_config in objects.items():
            if object_config == None:
                raise CompileError(
                    f"error with '{object_name}' for component {name}: configuration cannot be empty!"
                )

            if len(objects.items()) == 1:
                rendered_name = f"{name}"
            else:
                rendered_name = f"{name}-{object_name}"

            self.root.append(
                generating_class(
                    name=object_name,
                    rendered_name=rendered_name,
                    config=object_config,
                    component=component,
                    workload=workload,
                )
            )


class PrometheusRule(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "monitoring.coreos.com/v1"
        self.kwargs.kind = "PrometheusRule"
        super().new()

    def body(self):
        # TODO(ademaria) This name mangling is here just to simplify diff.
        # Change it once done
        component_name = self.kwargs.name
        self.kwargs.name = "{}.rules".format(component_name)
        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.add_namespace(component.get("namespace", inv.parameters.namespace))

        # TODO(ademaria): use `name` instead of `tesoro.rules`
        self.root.spec.setdefault("groups", []).append(
            {"name": "tesoro.rules", "rules": component.prometheus_rules.rules}
        )


class BackendConfig(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "cloud.google.com/v1"
        self.kwargs.kind = "BackendConfig"
        super().new()

    def body(self):
        component_name = self.kwargs.name
        self.kwargs.name = f"{component_name}-backend-config"
        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        self.root.spec = component.backend_config


class ServiceMonitor(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.kwargs.apiVersion = "monitoring.coreos.com/v1"
        self.kwargs.kind = "ServiceMonitor"
        super().new()

    def body(self):
        # TODO(ademaria) This name mangling is here just to simplify diff.
        # Change it once done
        component_name = self.kwargs.name
        workload = self.kwargs.workload
        self.kwargs.name = "{}-metrics".format(component_name)

        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        self.root.spec.endpoints = component.service_monitors.endpoints
        self.root.spec.jobLabel = name
        self.root.spec.namespaceSelector.matchNames = [inv.parameters.namespace]
        self.root.spec.selector.matchLabels = workload.spec.template.metadata.labels


class MutatingWebhookConfiguration(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "admissionregistration.k8s.io/v1beta1"
        self.kwargs.kind = "MutatingWebhookConfiguration"
        super().new()

    def body(self):
        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.root.webhooks = component.webhooks


class Role(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "rbac.authorization.k8s.io/v1"
        self.kwargs.kind = "Role"
        super().new()

    def body(self):
        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        self.root.rules = component.role.rules


class RoleBinding(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "rbac.authorization.k8s.io/v1"
        self.kwargs.kind = "RoleBinding"
        super().new()

    def body(self):
        super().body()
        default_role_ref = {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "Role",
            "name": self.kwargs.component.name,
        }
        default_subject = [
            {
                "kind": "ServiceAccount",
                "name": self.kwargs.component.name,
            }
        ]
        name = self.kwargs.name
        component = self.kwargs.component
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        self.root.roleRef = component.get("roleRef", default_role_ref)
        self.root.subjects = component.get("subject", default_subject)


class ClusterRole(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "rbac.authorization.k8s.io/v1"
        self.kwargs.kind = "ClusterRole"
        super().new()

    def body(self):
        super().body()
        name = self.kwargs.name
        component = self.kwargs.component
        self.root.rules = component.cluster_role.rules


class ClusterRoleBinding(k8s.Base):
    def new(self):
        self.need("component")
        self.kwargs.apiVersion = "rbac.authorization.k8s.io/v1"
        self.kwargs.kind = "ClusterRoleBinding"
        super().new()

    def body(self):
        super().body()
        default_role_ref = {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": self.kwargs.component.name,
        }
        default_subject = [
            {
                "kind": "ServiceAccount",
                "name": self.kwargs.component.name,
                "namespace": inv.parameters.namespace,
            }
        ]
        name = self.kwargs.name
        component = self.kwargs.component
        self.root.roleRef = component.get("roleRef", default_role_ref)
        self.root.subjects = component.get("subject", default_subject)


class PodDisruptionBudget(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.kwargs.apiVersion = "policy/v1beta1"
        self.kwargs.kind = "PodDisruptionBudget"
        super().new()

    def body(self):
        super().body()
        component = self.kwargs.component
        workload = self.kwargs.workload
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        if component.auto_pdb:
            self.root.spec.maxUnavailable = 1
        else:
            self.root.spec.minAvailable = component.pdb_min_available
        self.root.spec.selector.matchLabels = workload.spec.template.metadata.labels


class VerticalPodAutoscaler(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.kwargs.apiVersion = "autoscaling.k8s.io/v1beta2"
        self.kwargs.kind = "VerticalPodAutoscaler"
        super().new()

    def body(self):
        super().body()
        component = self.kwargs.component
        workload = self.kwargs.workload
        self.add_namespace(inv.parameters.namespace)
        self.add_labels(workload.metadata.labels)
        self.root.spec.targetRef.apiVersion = workload.apiVersion
        self.root.spec.targetRef.kind = workload.kind
        self.root.spec.targetRef.name = workload.metadata.name
        self.root.spec.updatePolicy.updateMode = component.vpa

        # TODO(ademaria) Istio blacklist is always desirable but add way to make it configurable.
        self.root.spec.resourcePolicy.containerPolicies = [
            {"containerName": "istio-proxy", "mode": "Off"}
        ]


class HorizontalPodAutoscaler(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.kwargs.apiVersion = "autoscaling/v2beta2"
        self.kwargs.kind = "HorizontalPodAutoscaler"
        super().new()

    def body(self):
        super().body()
        component = self.kwargs.component
        workload = self.kwargs.workload
        self.add_namespace(inv.parameters.namespace)
        self.add_labels(workload.metadata.labels)
        self.root.spec.scaleTargetRef.apiVersion = workload.apiVersion
        self.root.spec.scaleTargetRef.kind = workload.kind
        self.root.spec.scaleTargetRef.name = workload.metadata.name
        self.root.spec.minReplicas = component.hpa.min_replicas
        self.root.spec.maxReplicas = component.hpa.max_replicas
        self.root.spec.metrics = component.hpa.metrics


class VerticalPodAutoscaler(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.kwargs.apiVersion = "autoscaling.k8s.io/v1beta2"
        self.kwargs.kind = "VerticalPodAutoscaler"
        super().new()

    def body(self):
        super().body()
        component = self.kwargs.component
        workload = self.kwargs.workload
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        self.add_labels(workload.metadata.labels)
        self.root.spec.targetRef.apiVersion = workload.apiVersion
        self.root.spec.targetRef.kind = workload.kind
        self.root.spec.targetRef.name = workload.metadata.name
        self.root.spec.updatePolicy.updateMode = component.vpa

        # TODO(ademaria) Istio blacklist is always desirable but add way to make it configurable.
        self.root.spec.resourcePolicy.containerPolicies = [
            {"containerName": "istio-proxy", "mode": "Off"}
        ]


class PodSecurityPolicy(k8s.Base):
    def new(self):
        self.need("component")
        self.need("workload")
        self.kwargs.apiVersion = "policy/v1beta1"
        self.kwargs.kind = "PodSecurityPolicy"
        super().new()

    def body(self):
        super().body()
        component = self.kwargs.component
        workload = self.kwargs.workload
        self.add_namespace(component.get("namespace", inv.parameters.namespace))
        # relativly RAW input here, there is not much to be automatically generated
        self.root.spec = component.pod_security_policy.spec
        # Merge Dicts into PSP Annotations
        self.root.metadata.annotations = {
            **component.get("annotations", {}),
            **component.pod_security_policy.get("annotations", {}),
        }
        # Merge Dicts into PSP Labels
        self.root.metadata.labels = {
            **component.get("labels", {}),
            **component.pod_security_policy.get("labels", {}),
        }


def get_components():
    if "components" in inv.parameters:
        generator_defaults = inv.parameters.generators.manifest.default_config

        for name, component in inv.parameters.components.items():
            if component.get("enabled", True):
                if "application" in component:
                    application_defaults = inv.parameters.applications.get(
                        component.application, {}
                    ).get("component_defaults", {})
                    merge(generator_defaults, application_defaults)
                    if component.get("type", "undefined") in component.globals:
                        merge(
                            application_defaults,
                            component.globals.get(component.type, {}),
                        )
                    merge(application_defaults, component)

                merge(generator_defaults, component)
                component_type = component.get("type", generator_defaults.type)
                if (
                    component_type
                    in inv.parameters.generators.manifest.resource_defaults
                ):
                    component_defaults = (
                        inv.parameters.generators.manifest.resource_defaults[
                            component_type
                        ]
                    )
                    merge(component_defaults, component)

                component.name = name
                yield name, component


def generate_docs(input_params):
    obj = BaseObj()
    template = input_params.get("template_path", None)
    if template:
        for name, component in get_components():
            obj.root["{}-readme.md".format(name)] = j2(
                template,
                {
                    "service_component": component.to_dict(),
                    "inventory": inv.parameters.to_dict(),
                },
            )
    return obj


def generate_resource_manifests(input_params):
    obj = BaseObj()
    namespace_name = inv.parameters.namespace
    namespace = NameSpace(name=namespace_name)
    if namespace_name != "":
        obj.root["{}-namespace".format(namespace_name)] = namespace

    for (
        secret_name,
        secret_spec,
    ) in inv.parameters.generators.kubernetes.secrets.items():
        name = secret_spec.get("name", secret_name)
        secret = ComponentSecret(name=name, config=secret_spec)
        obj.root[f"{name}"] = secret

    if inv.parameters.generators.kubernetes.cert_manager:
        cert_manager = inv.parameters.generators.kubernetes.cert_manager

        for cert_name, cert_spec in cert_manager.certs.items():
            if cert_spec.get("type", "certmanager") == "certmanager":
                name = cert_spec.get("name", cert_name)
                cmc = CertManagerCertificate(name=name, config_spec=cert_spec)
                obj.root[f"{name}-cm-cert"] = cmc

        for issuer_name, issuer_spec in cert_manager.issuers.items():
            if issuer_spec.get("type", "certmanager") == "certmanager":
                name = issuer_spec.get("name", issuer_name)
                cmi = CertManagerIssuer(name=name, config_spec=issuer_spec)
                obj.root[f"{name}-cm-issuer"] = cmi

        for issuer_name, issuer_spec in cert_manager.clusterissuers.items():
            if issuer_spec.get("type", "certmanager") == "certmanager":
                name = issuer_spec.get("name", issuer_name)
                cmci = CertManagerClusterIssuer(name=name, config_spec=issuer_spec)
                obj.root[f"{name}-cmc-issuer"] = cmci
    return obj


def generate_ingress(input_params):
    # Only generate ingress manifest if istio not enabled
    if not inv.parameters.istio.enabled:
        obj = BaseObj()
        bundle = list()
        ingresses = inv.parameters.ingresses
        for name in ingresses.keys():
            ingress = Ingress(name=name, ingress=ingresses[name])

            if "managed_certificate" in ingresses[name]:
                certificate_spec = ingresses[name]
                certificate_name = certificate_spec.managed_certificate
                additional_domains = certificate_spec.get("additional_domains", [])
                domains = [certificate_name] + additional_domains
                ingress.add_annotations(
                    {"networking.gke.io/managed-certificates": certificate_name}
                )
                certificate = ManagedCertificate(name=certificate_name, domains=domains)
                obj.root["{}-managed-certificate".format(name)] = certificate

            obj.root["{}-ingress".format(name)] = ingress

        return obj


def generate_component_manifests(input_params):
    obj = BaseObj()
    for name, component in get_components():
        bundle_workload = []
        bundle_configs = []
        bundle_secrets = []
        bundle_service = []
        bundle_rbac = []
        bundle_scaling = []
        bundle_security = []

        workload = Workload(name=name, component=component)

        if component.schedule:
            workload = CronJob(name=name, component=component, job=workload)

        workload_spec = workload.root

        bundle_workload += [workload_spec]

        configs = GenerateMultipleObjectsForClass(
            name=name,
            component=component,
            generating_class=ComponentConfig,
            objects=component.config_maps,
            workload=workload_spec,
        )

        secrets = GenerateMultipleObjectsForClass(
            name=name,
            component=component,
            generating_class=ComponentSecret,
            objects=component.secrets,
            workload=workload_spec,
        )

        workload.add_volumes_for_objects(configs)
        workload.add_volumes_for_objects(secrets)

        bundle_configs += configs.root
        bundle_secrets += secrets.root

        if (
            component.vpa
            and inv.parameters.get("enable_vpa", True)
            and component.type != "job"
        ):
            vpa = VerticalPodAutoscaler(
                name=name, component=component, workload=workload_spec
            ).root
            bundle_scaling += [vpa]

        if component.pdb_min_available:
            pdb = PodDisruptionBudget(
                name=name, component=component, workload=workload_spec
            ).root
            bundle_scaling += [pdb]

        if component.hpa:
            hpa = HorizontalPodAutoscaler(
                name=name, component=component, workload=workload_spec
            ).root
            bundle_scaling += [hpa]

        if component.type != "job":
            if component.pdb_min_available or component.auto_pdb:
                pdb = PodDisruptionBudget(
                    name=name, component=component, workload=workload_spec
                ).root
                bundle_scaling += [pdb]
        if component.istio_policy:
            istio_policy = IstioPolicy(
                name=name, component=component, workload=workload_spec
            ).root
            bundle_security += [istio_policy]

        if component.pod_security_policy:
            psp = PodSecurityPolicy(
                name=name, component=component, workload=workload_spec
            ).root
            bundle_security += [psp]

        if component.service:
            service = Service(
                name=name,
                component=component,
                workload=workload_spec,
                service_spec=component.service,
            ).root
            bundle_service += [service]

        if component.additional_services:
            for service_name, service_spec in component.additional_services.items():
                service = Service(
                    name=service_name,
                    component=component,
                    workload=workload_spec,
                    service_spec=service_spec,
                ).root
                bundle_service += [service]

        if component.network_policies:
            policies = GenerateMultipleObjectsForClass(
                name=name,
                component=component,
                generating_class=NetworkPolicy,
                objects=component.network_policies,
                workload=workload_spec,
            ).root
            bundle_security += policies

        if component.webhooks:
            webhooks = MutatingWebhookConfiguration(name=name, component=component).root
            bundle_workload += [webhooks]

        if component.service_monitors:
            service_monitor = ServiceMonitor(
                name=name, component=component, workload=workload_spec
            ).root
            bundle_workload += [service_monitor]

        if component.prometheus_rules:
            prometheus_rule = PrometheusRule(name=name, component=component).root
            bundle_workload += [prometheus_rule]

        if component.role:
            role = Role(name=name, component=component).root
            bundle_rbac += [role]
            role_binding = RoleBinding(name=name, component=component).root
            bundle_rbac += [role_binding]

        if component.cluster_role:
            cluster_role = ClusterRole(name=name, component=component).root
            bundle_rbac += [cluster_role]
            cluster_role_binding = ClusterRoleBinding(
                name=name, component=component
            ).root
            bundle_rbac += [cluster_role_binding]

        if component.backend_config:
            backend_config = BackendConfig(name=name, component=component).root
            bundle_workload += [backend_config]

        if component.service_account.get("create", False):
            sa_name = component.service_account.get("name", name)
            sa = ServiceAccount(name=sa_name, component=component).root
            bundle_rbac += [sa]

        obj.root["{}-bundle".format(name)] = bundle_workload
        obj.root["{}-config".format(name)] = bundle_configs
        obj.root["{}-secret".format(name)] = bundle_secrets
        obj.root["{}-service".format(name)] = bundle_service
        obj.root["{}-rbac".format(name)] = bundle_rbac
        obj.root["{}-scaling".format(name)] = bundle_scaling
        obj.root["{}-security".format(name)] = bundle_security

    return obj


def generate_manifests(input_params):
    all_manifests = BaseObj()

    component_manifests = generate_component_manifests(input_params)
    ingress_manifests = generate_ingress(input_params)
    resource_manifests = generate_resource_manifests(input_params)

    all_manifests.root = component_manifests.root
    all_manifests.root.update(ingress_manifests.root)
    all_manifests.root.update(resource_manifests.root)

    return all_manifests


def main(input_params):
    whitelisted_functions = ["generate_manifests", "generate_docs"]
    function = input_params.get("function", "generate_manifests")
    if function in whitelisted_functions:
        return globals()[function](input_params)
