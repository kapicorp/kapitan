local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local classes = inv.classes;
local p = inv.parameters;

{

  data: {
    google_iam_policy: {
      org_iam_policy: {
        binding: [
          {
            role: obj.role,
            members: obj.members,
          }
          for obj in p.resources.org_iam.bindings
        ],

        audit_config: [
          {
            audit_log_configs: [
              {
                log_type: "DATA_READ",
              },
              {
                log_type: "DATA_WRITE",
              },
              {
                log_type: "ADMIN_READ",
              },
            ],
            service: "allServices",
          },

        ],

      },
    },

  },

  resource: {

    # Note: This is an authoritative policy
    google_organization_iam_policy: {
      org_iam_policy: {
        policy_data: "${data.google_iam_policy.org_iam_policy.policy_data}",
        org_id: p.org_id,
        lifecycle: {
          create_before_destroy: true,
        },
      },

    },

  },


}
