local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{

  resource: {
    # https://www.terraform.io/docs/providers/google/r/google_kms_key_ring.html
    google_kms_key_ring: {
      [keyring]: {
        name: keyring,
        location: p.region,
        depends_on: ["google_project_service.enable_kms_service"],

      }
      for keyring in std.objectFields(p.resources.kms)
    },
    # https://www.terraform.io/docs/providers/google/r/google_kms_crypto_key.html
    google_kms_crypto_key: {
      [keyring]: {
        name: key.name,
        /* key_ring: "${google_kms_key_ring." + keyring + ".self_link}", */
        key_ring: "${google_kms_key_ring.%s.self_link}" % keyring,
        [if "rotation_period" in key then "rotation_period"]: key.rotation_period,
        depends_on: ["google_project_service.enable_kms_service"],

      }
      for keyring in std.objectFields(p.resources.kms)
      for key in p.resources.kms[keyring].keys
    },

    google_project_service: {
      enable_kms_service: {
        service: "cloudkms.googleapis.com",
        disable_on_destroy: true,
        depends_on: ["google_project." + p.name],
      },
    },
  },

}
