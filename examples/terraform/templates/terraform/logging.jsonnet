local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{

  resource: {
    # https://www.terraform.io/docs/providers/google/r/logging_organization_sink.html
    [if "org_sinks" in p.resources.logging then "google_logging_organization_sink"]: {
      [sink.name]: {
        name: sink.name,
        org_id: p.org_id,
        destination: sink.destination,
        [if "filter" in sink then "filter"]: sink.filter,
        [if "include_children" in sink then "include_children"]: sink.include_children,

        depends_on: ["google_project." + p.name],

      }
      for sink in p.resources.logging.org_sinks
    },

    # https://www.terraform.io/docs/providers/google/r/logging_folder_sink.html
    [if "folder_sinks" in p.resources.logging then "google_logging_folder_sink"]: {
      [sink.name]: {
        name: sink.name,
        folder: p.folder_id,
        destination: sink.destination,
        [if "filter" in sink then "filter"]: sink.filter,
        [if "include_children" in sink then "include_children"]: sink.include_children,

        depends_on: ["google_project." + p.name],

      }
      for sink in p.resources.logging.folder_sinks
    },

    # https://www.terraform.io/docs/providers/google/r/logging_project_sink.html
    [if "proj_sinks" in p.resources.logging then "google_logging_project_sink"]: {
      [sink.name]: {
        name: sink.name,
        project: p.name,
        destination: sink.destination,
        [if "filter" in sink then "filter"]: sink.filter,
        [if "unique_writer_identity" in sink then "unique_writer_identity"]: sink.unique_writer_identity,

        depends_on: ["google_project." + p.name],

      }
      for sink in p.resources.logging.proj_sinks
    },

  },

}
