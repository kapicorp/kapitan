local statefulset = import "./statefulset.jsonnet";
local headless_service = import "./service.jsonnet";


{
  MySQL(name): {
    mysql_statefulset: statefulset.MySQLStatefulSet(name),
    mysql_service: headless_service.MySQLService(name)
  }
}
