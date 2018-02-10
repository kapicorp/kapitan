local statefulset = import "./statefulset.jsonnet";
local headless_service = import "./service.jsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

local name = inv.parameters.mysql.instance;

{
  mysql_statefulset: statefulset.MySQLStatefulSet(name),
  mysql_service: headless_service.MySQLService(name)
}
