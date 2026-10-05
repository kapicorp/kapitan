local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();

{
  target: inventory.parameters.target_name,
  env: inventory.parameters.env,
  app: inventory.parameters.app,
  component: inventory.parameters.component,
}