local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

{
  MySQLSecret(name): kube.Secret(name) {
    data: {
      "MYSQL_ROOT_PASSWORD": inv.parameters.mysql.users.root.password
    }
  }
}
