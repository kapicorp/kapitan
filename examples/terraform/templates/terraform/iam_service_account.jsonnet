local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{

  generate_name(role, member)::
    # Generate resouce name with valid characters
    # Receive:
    #   role: roles/owner
    #   member: "group:user@domain.com"
    # Return
    #   owner_user_domaincom
    assert std.type(role) == "string";
    assert std.type(member) == "string";
    local role_clean = std.strReplace(std.split(role, "/")[1], ".", "");
    local member_clean = std.strReplace(std.strReplace(std.split(member, ":")[1], "@", "_"), ".", "");
    role_clean + "_" + member_clean,

  check_service_account_name(name)::
    # check service account naming format
    # - must be between 6 and 30 characters.
    # - Service account ID must start with a lower case letter, followed by one or
    #    more lower case alphanumerical characters that can be separated by hyphens.
    assert std.type(name) == "string";
    assert std.length(name) >= 6 : "service account name [%s] must be between 6 and 30 characters" % name;
    local regex(x) = std.setMember(x, "-0123456789abcdefghijklmnopqrstuvwxyz");
    local validate(str) = std.join("", std.filter(regex, std.stringChars(str))) == str;
    assert validate(name) :
           "service account name [%s] must contain only lowercase alphanumerical or hyphens" % name;
    assert std.setMember(std.stringChars(name)[0], "abcdefghijklmnopqrstuvwxyz") :
           "service account name [%s] must start with lowercase letter" % name;
    name,

  resource: {

    google_service_account: {
      [$.check_service_account_name(obj.name)]: {
        account_id: obj.name,
        display_name: obj.name,
        depends_on: ["google_project." + p.name],
      }
      for obj in p.resources.iam.serviceaccounts
    },

    google_project_iam_member: {
      [$.generate_name(role, obj.member)]: {
        role: role,
        member: obj.member,
        depends_on: [
          "google_project." + p.name,
          "google_service_account." + obj.name,
        ],
        lifecycle: {
          create_before_destroy: true,
        },
      }
      for obj in p.resources.iam.serviceaccounts
      for role in obj.roles
    },

    google_service_account_iam_binding: {
      [if "workload_identity_members" in obj then obj.name + "-wi-bind"]: {
        service_account_id: "${google_service_account." + obj.name + ".name}",
        role: "roles/iam.workloadIdentityUser",
        members: obj.workload_identity_members,
        depends_on: std.prune([
          "google_project." + p.name,
          "google_service_account." + obj.name,
          if "workload_identity_members" in obj then "google_container_cluster." + p.resources.kubernetes[0].name,
        ]),
        lifecycle: {
          create_before_destroy: true,
        },
      }
      for obj in p.resources.iam.serviceaccounts
    },
  },

}
