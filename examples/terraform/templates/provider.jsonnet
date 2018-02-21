local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();


{
  provider: {
    google: {
      credentials: '${file("' + inv.parameters.provider.google.credentials + '")}',
      project: inv.parameters.provider.google.project,
      region: inv.parameters.provider.google.region,
      version: inv.parameters.provider.google.version,
      zone: inv.parameters.provider.google.zone,
    },
  },


  terraform: {
    backend: inv.parameters.terraform.backend,
  },
}
