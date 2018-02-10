local mysql = import "components/mysql/main.jsonnet";
local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();


mysql.MySQL(inv.parameters.mysql.instance_name)
