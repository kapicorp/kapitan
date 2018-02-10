local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();
local p = inventory.parameters;

{
    "namespace": kube.Namespace(p.namespace),
    "serviceaccount": kube.ServiceAccount("default")
}
