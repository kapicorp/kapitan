local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

local compute = import "compute.jsonnet";
local container = import "container.jsonnet";
local dns = import "dns.jsonnet";
local iam = import "iam.jsonnet";
local output = import "output.jsonnet";
local provider = import "provider.jsonnet";
local sql = import "sql.jsonnet";
local storage = import "storage.jsonnet";

{
  "output.tf": output,
  "provider.tf": provider,
  [if "compute" in inv.parameters.resources then "compute.tf"]: compute,
  [if "container" in inv.parameters.resources then "container.tf"]: container,
  [if "dns" in inv.parameters.resources then "dns.tf"]: dns,
  [if "iam" in inv.parameters.resources then "iam.tf"]: iam,
  [if "sql" in inv.parameters.resources then "sql.tf"]: sql,
  [if "storage" in inv.parameters.resources then "storage.tf"]: storage,
}
