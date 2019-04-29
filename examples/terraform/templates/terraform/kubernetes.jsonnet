local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

{

  resource: {
    google_container_cluster: {
      [cluster]: {
        initial_node_count: 1,
        min_master_version: inv.parameters.resources.container[cluster].min_master_version,
        name: cluster,
        node_version: inv.parameters.resources.container[cluster].node_version,
        depends_on: [
          "google_project_service.enable_container_service",
        ],

        # If this block is provided and both username and password are empty,
        # basic authentication will be disabled.
        master_auth: {
          username: "",
          password: "",
        },

      }
      for cluster in std.objectFields(inv.parameters.resources.container)
    },


    google_container_node_pool: {
      [pool]: {
        cluster: cluster,
        name: pool,
        node_config: {
          disk_size_gb: inv.parameters.resources.container[cluster].pools[pool].disk_size_gb,
          image_type: inv.parameters.resources.container[cluster].pools[pool].image_type,
          machine_type: inv.parameters.resources.container[cluster].pools[pool].machine_type,
          oauth_scopes: [
            "https://www.googleapis.com/auth/compute",
            "https://www.googleapis.com/auth/devstorage.read_only",
            "https://www.googleapis.com/auth/logging.write",
            "https://www.googleapis.com/auth/monitoring",
          ],
        },
        version: inv.parameters.resources.container[cluster].node_version,
        node_count: inv.parameters.resources.container[cluster].pools[pool].node_count,
        depends_on: ["google_container_cluster." + cluster],
      }
      for cluster in std.objectFields(inv.parameters.resources.container)
      for pool in std.objectFields(inv.parameters.resources.container[cluster].pools)
    },

    google_project_service: {
      enable_container_service: {
        service: "container.googleapis.com",
        disable_on_destroy: true,
      },
    },

  },

}
