local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

local cloudbuild = import "cloudbuild.jsonnet";
local dns = import "dns.jsonnet";
local iam = import "iam.jsonnet";
local iam_service_account = import "iam_service_account.jsonnet";
local kms = import "kms.jsonnet";
local kubernetes = import "kubernetes.jsonnet";
local logging = import "logging.jsonnet";
local monitoring = import "monitoring.jsonnet";
local output = import "output.jsonnet";
local provider = import "provider.jsonnet";
local pubsub = import "pubsub.jsonnet";
local storage = import "storage.jsonnet";
local modules = import "modules.jsonnet";

local name_in_resoures(name) = "resources" in p && name in p.resources;

{
  "output.tf": output,
  "provider.tf": provider,
  [if name_in_resoures("cloudbuild") then "cloudbuild.tf"]: cloudbuild,
  [if name_in_resoures("container") then "kubernetes.tf"]: kubernetes,
  [if name_in_resoures("dns") then "dns.tf"]: dns,
  [if name_in_resoures("iam") && "serviceaccounts" in p.resources.iam then "iam_service_account.tf"]: iam_service_account,
  [if name_in_resoures("iam") then "iam.tf"]: iam,
  [if name_in_resoures("kms") then "kms.tf"]: kms,
  [if name_in_resoures("logging") then "logging.tf"]: logging,
  [if name_in_resoures("monitoring") then "monitoring.tf"]: monitoring,
  [if name_in_resoures("pubsub") then "pubsub.tf"]: pubsub,
  [if name_in_resoures("storage") then "storage.tf"]: storage,
  [if "modules" in p then "modules.tf"]: modules

}
