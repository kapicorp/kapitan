local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();


{
  provider: {
    google: {
      project: inv.parameters.name,
      version: inv.parameters.provider.google.version,
      region: inv.parameters.region,
      zone: inv.parameters.zone,
    },
  },


  terraform: {
    backend: inv.parameters.terraform.backend,
    required_version: inv.parameters.terraform.required_version,
  },

  assert
  std.startsWith(inv.parameters.zone, inv.parameters.region) :
    "zone and region don't match",

  assert
  std.objectHas(self, "provider") :
    "Provider is required. None defined",

  assert
  std.objectHas(self.provider.google, "version") :
    "Provider version is required",

  assert
  std.count(inv.parameters.valid_values.zones, self.provider.google.zone) == 1 :
    "zone " + self.provider.google.zone + " is invalid\n" +
    "valid zones are: " + inv.parameters.valid_values.zones,

}
