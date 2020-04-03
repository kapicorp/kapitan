local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

{
  MySQLSecret(name): kube.Secret(name) {
    data: {
      "MYSQL_ROOT_PASSWORD": inv.parameters.mysql.users.root.password,
      "MYSQL_ROOT_PASSWORD_SHA256": inv.parameters.mysql.users.root.password_sha256
    }
  }
}

{
  MySQLSecret_subvar(name): kube.Secret(name) {
    data: {
      "MYSQL_ROOT_PASSWORD": inv.parameters.mysql.users.root.password_subvar,
      "MYSQL_ROOT_PASSWORD_SHA256": inv.parameters.mysql.users.root.password_sha256_subvar
    }
  }
}
