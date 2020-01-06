local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();
local p = inv.parameters;

{

  data: {
    google_iam_policy: {
      [bucket.name]: {
        # restricted option removes default roles and only adds the iam_policy the bucket defines
        binding: if "restricted" in bucket && bucket.restricted then bucket.iam_policy else [
          # These are default roles that are applied when a bucket is created
          # More info on https://www.terraform.io/docs/providers/google/r/storage_bucket_iam.html#google_storage_bucket_iam_policy-1
          {
            members: [
              "projectEditor:" + p.name,
            ],
            role: "roles/storage.legacyBucketOwner",
          },
          {
            members: [
              "projectEditor:" + p.name,
            ],
            role: "roles/storage.legacyBucketWriter",
          },
          {
            members: [
              "projectViewer:" + p.name,
            ],
            role: "roles/storage.legacyBucketReader",
          },
        ] + bucket.iam_policy,
      }
      for bucket in p.resources.storage
      if "iam_policy" in bucket
    },
  },


  resource: {

    google_storage_bucket: {
      [bucket.name]: {
        name: bucket.name,
        location: if "location" in bucket then bucket.location else p.region,
        storage_class: bucket.storage_class,
        versioning: {
          enabled: bucket.versioning,
        },
        depends_on: ["google_project." + p.name],
        lifecycle: {
          prevent_destroy: true,
        },
        # restricted option also disables ACL and only allows IAM roles, see more https://cloud.google.com/storage/docs/bucket-policy-only
        [if "restricted" in bucket && bucket.restricted then "bucket_policy_only"]: true,
        [if "retention_policy" in bucket then "retention_policy"]: bucket.retention_policy,
        [if "lifecycle_rule" in bucket then "lifecycle_rule"]: bucket.lifecycle_rule,
      } + if p.logging.logging_bucket_name != bucket.name then {
        logging: {
          log_bucket: p.logging.logging_bucket_name,
          log_object_prefix: p.logging.logging_storage_prefix + "/" +
                             p.name + "/" +
                             bucket.name + "/",
        },
      } else {}
      for bucket in p.resources.storage
    },

    google_storage_bucket_iam_policy: {
      [bucket.name]: {
                       bucket: bucket.name,
                       policy_data: "${data.google_iam_policy." + bucket.name + ".policy_data}",
                     }
                     + if "restricted" in bucket && bucket.restricted then {
                       depends_on: ["google_storage_bucket." + bucket.name],
                     } else {
                       depends_on: ["google_storage_bucket_acl." + bucket.name],
                     }
      for bucket in p.resources.storage
      if "iam_policy" in bucket
    },
    # It's recommended to use IAM permissions as a primary way of setting
    # Access controls to buckets. The below code is mainly to set a predefined ACL.
    # https://cloud.google.com/storage/docs/access-control/
    google_storage_bucket_acl: {
      # Buckets with 'restricted: true' enable https://cloud.google.com/storage/docs/bucket-policy-only,
      # which does not support ACLs and relies solely on IAM (default no-access/private).
      [if !bucket.restricted then bucket.name]: {
        bucket: bucket.name,
        depends_on: ["google_storage_bucket." + bucket.name],
        predefined_acl: "projectPrivate",
      }
      for bucket in p.resources.storage
    },
  },
}
