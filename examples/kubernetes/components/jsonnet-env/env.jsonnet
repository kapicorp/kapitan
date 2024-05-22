local kap = import 'lib/kapitan.libjsonnet';
local inventory = kap.inventory();



{
  env: {
    applications: inventory.applications,
    classes: inventory.classes,
    parameters: inventory.parameters {
      ["_kapitan_"]:: std.get(inventory.parameters, "_kapitan_"),  // Ignore this in compile tests because reclass doesn't support it
      ["_reclass_"]: std.get(inventory.parameters, "_reclass_") {
        ["environment"]:: "base" // ignore because unused
      }
    },
    exports: inventory.exports,
  },
}
