local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

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

local svc = kube.Service("nginx") {
      target_pod:: deployment.spec.template,
      target_container_name:: "nginx",
      type: "NodePort",
};

{
    "app-service": svc,
    "app-deployment": deployment,
}
