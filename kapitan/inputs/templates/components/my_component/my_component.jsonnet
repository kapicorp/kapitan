local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();

{
  example: {
    test: inventory.parameters.your_component.some_parameter
  }
}
