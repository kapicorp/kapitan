local kap = import "lib/kapitan.libjsonnet";
local inventory = kap.inventory();

{
  ['Dockerfile.' + file.name]: kap.jinja2_template("templates/Dockerfile", file)
  for file in inventory.parameters.dockerfiles
}
