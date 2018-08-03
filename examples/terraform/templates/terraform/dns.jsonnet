local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

{

  remove_dots(str)::
    assert std.type(str) == "string";
    std.join("", std.split(str, ".")),


  resource: {

    google_dns_managed_zone: {
      [$.remove_dots(zone)]: {
        name: $.remove_dots(zone),
        dns_name: zone + ".",  # add mandatory dot at the end of zone
        description: "DNS zone for " + zone,
      }
      for zone in std.objectFields(inv.parameters.resources.dns)
    },

    google_dns_record_set: {
      [$.remove_dots(zone + "_" + set.name + "_" + set.type)]: set {
        managed_zone: $.remove_dots(zone),
      }
      for zone in std.objectFields(inv.parameters.resources.dns)
      for set in inv.parameters.resources.dns[zone]
    },

  },

}
