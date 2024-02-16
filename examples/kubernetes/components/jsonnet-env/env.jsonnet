local kap = import 'lib/kapitan.libjsonnet';
local inventory = kap.inventory();

{
  env: {
    applications: inventory.applications,
    classes: inventory.classes,
    parameters: inventory.parameters,
    exports: inventory.exports,
  },
}
