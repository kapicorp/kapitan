# Support for [Google Secret Manager](https://cloud.google.com/secret-manager/)

This feature will enable users to retrieve secrets from Google Secret Manager API using the `gsm` keyword.

## Specification

`project_id` uniquely identifies GCP projects, and it needs to be made accessible to kapitan in one of the following ways:

- As a part of target

```yaml
parameters:
  kapitan:
    secrets:
      gsm:
        project_id: Project_Id
```

- As a flag

```shell
kapitan refs --google-project-id=<Project_Id> --write gsm:/path/to/secret_id -f secret_id_file.txt
```

- As an environment variable

```shell
export PROJECT_ID=<Project_Id>
```

## Using a secret

In GCP, a secret contains one or more secret versions, along with its metadata. The actual contents of a secret are stored in a secret version. Each secret is identified by a name. We call that variable `secret_id` e.g. _my\_treasured\_secret_.
The URI of the secret becomes `projects/<Project_Id>/secrets/my_treasured_secret`

The following command will be used to add a `secret_id` to kapitan.

```shell
echo "my_treasured_secret"  | kapitan refs --write gsm:path/to/secret_inside_kapitan -t <target_name> -f -
```

The `-t <target_name>` is used to get the information about Project_ID.

The `secret_id` is Base64 encoded and stored in `path/to/secret_inside_kapitan` as

```yaml
data: bXlfdHJlYXN1cmVkX3NlY3JldAo=
encoding: original
type: gsm
gsm_params:
  project_id: Project_ID
```

## referencing a secret

Secrets can be refered using `?{gsm:path/to/secret_id:version_id}`
e.g.

```yaml
parameter:
    mysql:
        storage: 10G
        storage_class: standard
        image: mysql:latest
        users:
            root:
                password: ?{gsm:path/to/secret_id:version_id}
```

Here, `version_id` will be an optional argument. By default it will point to `latest`.

## Revealing a secret

After compilation, the secret reference will be postfixed with 8 characters from the sha256 hash of the retrieved password

```yaml
apiVersion: v1
data:
  MYSQL_ROOT_PASSWORD: ?{gsm:path/to/secret_id:version_id:deadbeef}
kind: Secret
metadata:
  labels:
    name: example-mysql
  name: example-mysql
  namespace: minikube-mysql
type: Opaque
```

To reveal the secret, the following command will be used
`$ kapitan ref --reveal -f compiled/file/containing/secret`

## Dependencies

- [google-cloud-secret-manager](https://github.com/googleapis/python-secret-manager)

_note_ Kapitan will not be responsible for authentication or access management to GCP
