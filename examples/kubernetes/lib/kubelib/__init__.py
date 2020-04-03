from kapitan.inputs.kadet import BaseObj, inventory

inv = inventory()


class Deployment(BaseObj):
    def new(self):
        self.need("name", "name string needed")
        self.need("labels", "labels dict needed")
        self.need("containers", "containers dict needed")
        self.update_root("lib/kubelib/deployment.yml")

    def body(self):
        self.root.metadata.name = self.kwargs.name
        self.root.metadata.namespace = inv.parameters.target_name
        self.root.spec.template.metadata.labels = self.kwargs.labels
        self.root.spec.template.spec.containers = self.kwargs.containers


class Service(BaseObj):
    def new(self):
        self.need("name", "name string needed")
        self.need("labels", "labels dict needed")
        self.need("ports", "ports dict needed")
        self.need("selector", "selector dict needed")
        self.update_root("lib/kubelib/service.yml")

    def body(self):
        self.root.metadata.name = self.kwargs.name
        self.root.metadata.labels = self.kwargs.labels
        self.root.metadata.namespace = inv.parameters.target_name
        self.root.spec.ports = self.kwargs.ports
        self.root.spec.selector = self.kwargs.selector


class Container(BaseObj):
    def new(self):
        self.need("name")
        self.need("image")
        self.need("ports", "ports list of dict needed")

    def body(self):
        self.root.name = self.kwargs.name
        self.root.image = self.kwargs.image
        self.root.ports = self.kwargs.ports
