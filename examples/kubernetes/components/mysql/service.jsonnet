local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();

local namespace = inventory.parameters.namespace;
local instance_name = inventory.parameters.mysql.instance_name;


{
    apiVersion: "v1",
    kind: "Service",
    spec: {
        ports: [
            {
                name: "mysql",
                port: 3306,
                targetPort: "mysql",
            },
        ],
        selector: { name: instance_name },
        clusterIP: "None",
        type: "ClusterIP",
    },

    metadata: {
        name: instance_name,
        namespace: namespace,
        labels: { name: instance_name },
    },
}
