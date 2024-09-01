// cover https://github.com/kapicorp/kapitan/issues/434
local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();
local p = inventory.parameters;

'my plainref is: ' + p.my_plainref

