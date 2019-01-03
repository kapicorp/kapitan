from kapitan.inputs.kadet import BaseObj, inventory
inv = inventory()


class Deployment(BaseObj):
    def new(self):
        self.need("_name", "name string needed")
        self.need("_labels", "labels dict needed")
        self.need("_containers", "containers dict needed")
        self.root_from_yaml("lib/kubelib/deployment.yml")

    def body(self):
        self.root.metadata.name = self._name
        self.root.metadata.namespace = inv.parameters.target_name
        self.root.spec.template.metadata.labels = self._labels
        self.root.spec.template.spec.containers = self._containers


class Service(BaseObj):
    def new(self):
        self.need("_name", "name string needed")
        self.need("_labels", "labels dict needed")
        self.need("_ports", "ports dict needed")
        self.need("_selector", "selector dict needed")
        self.root_from_yaml("lib/kubelib/service.yml")

    def body(self):
        self.root.metadata.name = self._name
        self.root.metadata.labels = self._labels
        self.root.metadata.namespace = inv.parameters.target_name
        self.root.spec.ports = self._ports
        self.root.spec.selector = self._selector


class Container(BaseObj):
    def new(self):
        self.need("name")
        self.need("image")
        self.need("ports", "ports list of dict needed")
