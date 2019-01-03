from kapitan.inputs import kadet
kubelib = kadet.load_from_search_paths("kubelib")
inv = kadet.inventory()

name = "nginx"
labels = kadet.BaseObj(app=name)
nginx_container = kubelib.Container(name=name, image=inv.parameters.nginx.image, ports=[{"containerPort": 80}])

svc_selector = {"app": name}
svc_port = kadet.BaseObj()
svc_port.root.name = "http"
svc_port.root.port = 80
svc_port.root.targetPort = 80


def main():
    output = kadet.BaseObj()
    output.root.nginx_deployment = kubelib.Deployment(_name=name, _labels=labels, _containers=[nginx_container])
    output.root.nginx_service = kubelib.Service(_name=name, _labels=labels, _ports=[svc_port], _selector=svc_selector)
    return output
