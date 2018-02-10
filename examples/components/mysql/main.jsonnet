local statefulset = import "./statefulset.jsonnet";
local headless_service = import "./service.jsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local secret = import "./secret.jsonnet";

local name = inv.parameters.mysql.instance_name;

{
  mysql_statefulset: statefulset.MySQLStatefulSet(name, self.mysql_secret),
  mysql_service: headless_service.MySQLService(name),
  mysql_secret: secret.MySQLSecret(name)
}
