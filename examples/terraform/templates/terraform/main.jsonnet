local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

local output = import "output.jsonnet";
local provider = import "provider.jsonnet";

local dns = import "dns.jsonnet";
local kubernetes = import "kubernetes.jsonnet";


{
  "output.tf": output,
  "provider.tf": provider,
  [if "container" in inv.parameters.resources then "kubernetes.tf"]: kubernetes,
  [if "dns" in inv.parameters.resources then "dns.tf"]: dns,
}
