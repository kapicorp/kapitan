local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

{
  data: {
    template_file: {
      readme: {
        template: kap.jinja2_template("templates/terraform/README.md.j2", inv),
      },
    },
  },

  output: {
    "README.md": {
      value: "${data.template_file.readme.rendered}",
      sensitive: true,
    },
  },

}
