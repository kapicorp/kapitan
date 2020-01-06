local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{

  resource: {

    google_cloudbuild_trigger: {
      # Name can only contain letters, numbers, dashes, and underscores.
      [std.strReplace(trigger.description, " ", "_")]: {
        filename: trigger.filename,
        description: trigger.description,
        trigger_template: {
          [if "branch_name" in trigger then "branch_name"]: trigger.branch_name,
          [if "repo_name" in trigger then "repo_name"]: trigger.repo_name,
        },

        depends_on: ["google_project_service.enable_cloudbuild_service"],
      }
      for trigger in p.resources.cloudbuild.triggers
    },

    google_project_service: {
      enable_cloudbuild_service: {
        service: "cloudbuild.googleapis.com",
        disable_on_destroy: true,
        depends_on: ["google_project." + p.name],
      },
    },

  },

}
