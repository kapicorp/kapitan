## Kapitan: CI/CD usage

The [Docker image](https://hub.docker.com/r/deepmind/kapitan/tags/) (`deepmind/kapitan:ci`) ([Dockerfile](./ci/Dockerfile)) comes pre-packaged with `gcloud`, `gsutil`, `bq`, `kubectl` and `kapitan`.

### Example workflow - Deploy to GKE

The following commands are run using the `deepmind/kapitan:ci` Docker image.

1. Compile:

   ```shell
   kapitan compile

   Compiled app (2.23s)
   ```

1. Setup gcloud and GKE credentials:

   ```shell
   echo "$GCP_SA_KEY_FROM_CI_SECRETS" > service_account_key.json
   gcloud auth activate-service-account --key-file service_account_key.json
   gcloud container clusters get-credentials CLUSTER --zone ZONE --project GCP_PROJECT_ID
   ```

1. Setup kubectl:

   ```shell
   kubectl config set-context CLUSTER_CONTEXT --cluster CLUSTER --user USER --namespace NAMESPACE
   kubectl config use-context CLUSTER_CONTEXT
   ```

1. Deploy:

   ```shell
   kubectl apply -f compiled/app/manifests/
   ```
