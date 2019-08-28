local kube = import "lib/kube.libjsonnet";
local deployment = import "./deployment.jsonnet";

local svc = kube.Service("nginx") {
      target_pod:: deployment.nginx_deployment.spec.template,
      target_container_name:: "nginx",
      type: "NodePort",
};


{
    nginx_svc: svc
}