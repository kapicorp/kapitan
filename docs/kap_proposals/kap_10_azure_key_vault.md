# Support for [Azure Key Management](https://docs.microsoft.com/en-us/azure/key-vault/)

This feature will enable users to encrypt secrets using keys stored in Azure's Key Vault. The `azkms` keyword will be used to access the azure key management backend.

## Specification

`key_id` uniquely identifies an Azure key object and it's version stored in Key Vault. It is of the form `https://{keyvault-name}.vault.azure.net/{object-type}/{object-name}/{object-version}`.
It needs to be made accessible to kapitan in one of the following ways:

- As a part of target
```yaml
parameters:
  kapitan:
    secrets:
      azkms:
        key: key_id #eg https://kapitanbackend.vault.azure.net/keys/myKey/deadbeef
```

- As a flag
```shell
$ kapitan refs --key=<key_id> --write azkms:/path/to/secret -f file_with_secret_data.txt
```

## Using a key to encrypt a secret

The following command will be used to encrypt a secret (using the specified key from Key Vault) and save it in the `refs-path` along with it's metadata
```shell
$ echo "my_treasured_secret"  | kapitan refs --write azkms:path/to/secret_inside_kapitan -t <target_name> -f -
```
The `-t <target_name>` is used to get the information about key_id.

Once the secret is Base64 encoded and encrypted using the key, it will be stored in `path/to/secret_inside_kapitan` as
```yaml
data: bXlfdHJlYXN1cmVkX3NlY3JldAo=
encoding: original
key: https://kapitanbackend.vault.azure.net/keys/myKey/deadbeef
type: azkms
```

*note* Cryptographic algorithm used for encryption would be _rsa-oaep-256_. Optimal Asymmetric Encryption Padding (OAEP) is a padding scheme often used together with RSA encryption.

## referencing a secret
Secrets can be refered using `?{azkms:path/to/secret_id}`
e.g.
```yaml
parameter:
    mysql:
        storage: 10G
        storage_class: standard
        image: mysql:latest
        users:
            root:
                password: ?{azkms:path/to/secret}
```

## Revealing a secret

After compilation, the secret reference will be postfixed with 8 characters from the sha256 hash of the retrieved password/secret
```yaml
apiVersion: v1
data:
  MYSQL_ROOT_PASSWORD: ?{azkms:path/to/secret:deadbeef}
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

* [azure-keyvault-keys](https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/keyvault/azure-keyvault-keys)
* [azure-identity](https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/identity/azure-identity)

*note* Kapitan will not be responsible for authentication or access management to Azure