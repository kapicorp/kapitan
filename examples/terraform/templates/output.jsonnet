local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

{
  data: {
    template_file: {
      readme: {
        template: kap.jinja2_template("templates/README.md.j2", inv),
      },
    },
  },

  resource: {
    null_resource: {
      readme_generator: {
        triggers: {
          template_rendered: "${data.template_file.readme.rendered}",
        },

        provisioner: [
          {
            "local-exec": {
              command: "echo '${data.template_file.readme.rendered}' > ../README.md",
            },
          },
        ],
      },
    },
  },

  output: {
    "README.md": {
      value: "\n${data.template_file.readme.rendered}",
    },
  },

}
