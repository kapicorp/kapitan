local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{
  generate_name(obj)::
    # Generate resouce name with valid characters
    # Receive:
    #   some-name.something
    # Return
    #   some_name_something
    assert std.type(obj) == "string";
    local clean_name = std.strReplace(std.strReplace(obj, ".", "_"), "-", "_");
    clean_name,

  resource: {

    # https://www.terraform.io/docs/providers/google/r/pubsub_topic.html
    [if "topics" in p.resources.pubsub then "google_pubsub_topic"]: {
      [$.generate_name(topic.name)]: {
        name: topic.name,
        project: topic.project,

        message_storage_policy: topic.message_storage_policy,
      }
      for topic in p.resources.pubsub.topics
    },

    # https://www.terraform.io/docs/providers/google/r/pubsub_subscription.html
    [if "subscriptions" in p.resources.pubsub then "google_pubsub_subscription"]: {
      [$.generate_name(subscription.name)]: {
        project: subscription.project,
        name: subscription.name,
        topic: subscription.topic_name,

        depends_on: ["google_pubsub_topic." + $.generate_name(subscription.topic_name)],
      }
      for subscription in p.resources.pubsub.subscriptions
    },

  },
}
