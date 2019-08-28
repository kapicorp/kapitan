local svc = import "./service.jsonnet";
local deployment = import "./deployment.jsonnet";


{
    "app-service": svc.nginx_svc,
    "app-deployment": deployment.nginx_deployment,
}
