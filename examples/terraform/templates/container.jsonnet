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
        node_count: inv.parameters.resources.container[cluster].pools[pool].node_count,
      }
      for cluster in std.objectFields(inv.parameters.resources.container)
      for pool in std.objectFields(inv.parameters.resources.container[cluster].pools)
    },

    # Code below is weird but is only needed because when you create a new cluster, it ALWAYS creates
    # a default-pool. Code below deletes the default-pool.
    # exec will only run once on cluster creation
    # More info on https://github.com/terraform-providers/terraform-provider-google/issues/773
    null_resource: {
      [cluster + "_delete_default-node-pool"]: {
        triggers: {
          cluster_name: "${google_container_cluster." + cluster + ".name}",
        },

        provisioner: [
          {
            "local-exec": {
              command: "gcloud container node-pools --project=" + inv.parameters.name +
                       " --zone=" + inv.parameters.main_zone +
                       " --quiet delete default-pool --cluster " + cluster,
            },
          },
        ],
        depends_on: ["google_container_cluster." + cluster]
      }
      for cluster in std.objectFields(inv.parameters.resources.container)
    },

  },

}
