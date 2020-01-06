local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{

  generate_name(obj, member)::
    # Generate resouce name with valid characters
    # Receive:
    #   role: roles/owner
    #   member: "group:user@domain.com"
    # Return
    #   owner_user_domaincom
    local role = obj.role;
    assert std.type(role) == "string";
    assert std.type(member) == "string";
    local role_clean = std.strReplace(std.split(role, "/")[1], ".", "");
    local member_clean = if "clean_name" in obj then obj.clean_name else std.strReplace(std.strReplace(std.split(member, ":")[1], "@", "_"), ".", "");
    role_clean + "_" + member_clean,

  resource: {
    [if "bindings" in p.resources.iam then "google_project_iam_member"]: {
      [$.generate_name(obj, member)]: {
        role: obj.role,
        member: member,
        depends_on: ["google_project." + p.name],
        lifecycle: {
          create_before_destroy: true,
        },
        local prefix_list = ["user", "serviceAccount", "group", "mdb"],
        local prefix_member = if "clean_name" in obj then "serviceAccount" else std.split(member, ":")[0],
        assert
        std.count(prefix_list, prefix_member) == 1 :
          "IAM member MUST start with one of (case sensitive): %s. Received: %s" % [prefix_list, member],

      }
      for obj in p.resources.iam.bindings
      for member in obj.members
    },

    [if "custom_roles" in p.resources.iam then "google_project_iam_custom_role"]: {
      [std.strReplace(obj.id, ".", "_")]: {
        role_id: obj.id,
        title: obj.title,
        permissions: obj.permissions,
      }
      for obj in p.resources.iam.custom_roles
    },
  },
}
