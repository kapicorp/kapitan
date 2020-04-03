local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{

  resource: {

    # https://www.terraform.io/docs/providers/google/r/monitoring_notification_channel.html
    google_monitoring_notification_channel: {
      [channel.name]: {
        display_name: channel.display_name,
        type: channel.type,
        labels: channel.labels,
        [if "description" in channel then "description"]: channel.description,
        [if "enabled" in channel then "enabled"]: channel.enabled,
        project: p.name,
        depends_on: [
          "google_project_service.enable_stackdriver_service",
        ],
      }
      for channel in p.resources.monitoring.notification_channels
    },

    # https://www.terraform.io/docs/providers/google/r/monitoring_alert_policy.html
    google_monitoring_alert_policy: {
      [policy.name]: {
        display_name: policy.display_name,
        combiner: policy.combiner,
        conditions: policy.conditions,
        [if "enabled" in policy then "enabled"]: policy.enabled,
        [if "notification_channels" in policy then "notification_channels"]: policy.notification_channels,
        [if "user_labels" in policy then "user_labels"]: policy.user_labels,
        [if "documentation" in policy then "documentation"]: policy.documentation,
        project: p.name,
        depends_on: [
          "google_project_service.enable_stackdriver_service",
        ],
      }
      for policy in p.resources.monitoring.alert_policies
    },
  },

  variable: {
    pagerduty_integration_key: {
      type: "string",
      default: "",
    },
  },

}
