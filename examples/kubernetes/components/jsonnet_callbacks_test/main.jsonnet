local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();
local p = inventory.parameters;

{
    "01_yaml_load": {json_str: kap.yaml_load("components/busybox/pod.yml")},
}
