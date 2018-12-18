local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();


# you can choose to move this container to a different file if it starts to get
# too complicated. In this example it's here for simplification
local mysql_container = kube.Container("mysql") {
  # rather than passing arguments with jsonnet, you can inject values straight
  # into the right place thanks to the inventory. We find it makes things easier, but some
  # might not like it. Again... your choice. One more thing. We don't do defaults.
  # If something is not set we don't want it to go silent.
  image: inv.parameters.mysql.image,

  ports_+: {
    # We tend to draw a line when making everything a configurable option.
    # If you find yourself altering the default mysql port, you'd better have a real case.
    # Some things are best hardcoded until a real need comes.
    # In that case, it's as simple as injecting the inventory field.
    mysql: { containerPort: 3306 },
  },

  env_+: if ("env" in inv.parameters.mysql) then inv.parameters.mysql.env else {}
};

local claim = {
  data: {
    storage: inv.parameters.mysql.storage,
    storageClass: inv.parameters.mysql.storage_class,
  }
};

{
  MySQLStatefulSet(name, secret): kube.StatefulSet(name) {
    spec+: {
      volumeClaimTemplates_:: claim,
      template+: {
        spec+: {
          containers_+: {
            mysql: mysql_container + { env_+: { MYSQL_ROOT_PASSWORD: kube.SecretKeyRef(secret, "MYSQL_ROOT_PASSWORD")} }
          },
        },
      },
    },
  },
}
