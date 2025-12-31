import base64
import hashlib
import os

from kapitan.inputs.kadet import BaseObj, inventory

from . import k8s


inv = inventory(lazy=True)


class SharedConfig:
    """Shared class to use for both Secrets and ConfigMaps classes."""

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

    def add_directory(self, directory, encode=False):
        if directory and os.path.isdir(directory):
            for filename in os.listdir(directory):
                with open(f"{directory}/{filename}") as f:
                    file_content = f.read()
                    self.add_item(
                        filename, file_content, request_encode=encode, stringdata=False
                    )

    def add_data(self, data):
        for key, spec in data.items():
            encode = spec.get("b64_encode", False)
            if "value" in spec:
                value = spec.get("value")
            if "file" in spec:
                with open(spec.file) as f:
                    value = f.read()
            self.add_item(key, value, request_encode=encode, stringdata=False)

    def add_string_data(self, string_data, encode=False):
        for key, spec in string_data.items():
            if "value" in spec:
                value = spec.get("value")
            if "file" in spec:
                with open(spec.file) as f:
                    value = f.read()
            self.add_item(key, value, request_encode=encode, stringdata=True)

    def versioning(self):
        keys_of_interest = ["data", "binaryData", "stringData"]
        subset = {
            key: value
            for key, value in self.root.dump().items()
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
        if self.config.versioned:
            self.versioning()


class Secret(k8s.Base):
    def new(self):
        self.kwargs.apiVersion = "v1"
        self.kwargs.kind = "Secret"
        super().new()

    def add_item(self, key, value, request_encode=False, stringdata=False):
        encode = not stringdata and request_encode
        field = "stringData" if stringdata else "data"
        self.root[field][key] = SharedConfig.encode_string(value) if encode else value


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
        if self.config.versioned:
            self.versioning()


def generate_resource_manifests(input_params):
    obj = BaseObj()

    for (
        secret_name,
        secret_spec,
    ) in inv.parameters.generators.kubernetes.secrets.items():
        name = secret_spec.get("name", secret_name)
        secret = ComponentSecret(name=name, config=secret_spec)
        namespace_name = secret_spec.get("namespace", inv.parameters.namespace)
        obj.root[f"{namespace_name}/{name}"] = secret

    for (
        config_name,
        config_spec,
    ) in inv.parameters.generators.kubernetes.configs.items():
        name = config_spec.get("name", config_name)
        config_map = ComponentConfig(name=name, config=config_spec)
        namespace_name = config_spec.get("namespace", inv.parameters.namespace)
        obj.root[f"{namespace_name}/{name}"] = config_map

    return obj


def main(input_params):
    return generate_resource_manifests(input_params)
