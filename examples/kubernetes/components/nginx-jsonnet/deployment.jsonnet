local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

local myContainers = kube.Container("nginx") {
    image: inv.parameters.nginx.image,
    ports_+: {
        http: {containerPort: 80}
    },
};

local deployment = kube.Deployment("nginx") {
    spec+: {
        replicas: inv.parameters.nginx.replicas,
        template+: {
            spec+: {
                containers_+: {
                    nginx: myContainers
                },
            }
        }
    }
};

{
    nginx_deployment: deployment
}