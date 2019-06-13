# Hashicorp Vault 

This feature allows user to fetch secrets from [Hashicorp Vault](https://www.vaultproject.io/), an online Kapitan Secret backend `vault` will be introduced. 

Author: @vaibhavk

## Specification

The following variables need to be exported to the environment where you run this script in order to authenticate to your HashiCorp Vault instance:
    * VAULT_ADDR: url for vault
    * VAULT_SKIP_VERIFY=true: if set, do not verify presented TLS certificate before communicating with Vault server. Setting this variable is not recommended except during testing
    * VAULT_AUTHTYPE: authentication type to use: token, userpass, github, ldap, approle
    * VAULT_TOKEN: token for vault or file (~/.vault-tokens) 
    * VAULT_ROLE_ID: (required by approle)
    * VAULT_SECRET_ID: (required by approle)
    * VAULT_USER: username to login to vault
    * VAULT_PASSWORD: password to login to vault
    * VAULT_CLIENT_KEY: path to an unencrypted PEM-encoded private key matching the client certificate
    * VAULT_CLIENT_CERT: path to a PEM-encoded client certificate for TLS authentication to the Vault server
    * VAULT_CACERT: path to a PEM-encoded CA cert file to use to verify the Vault server TLS certificate
    * VAULT_CAPATH: path to a directory of PEM-encoded CA cert files to verify the Vault server TLS certificate
    * VAULT_NAMESPACE: specify the Vault Namespace, if you have one

The following command creates a secret from _somefile.txt_ using the secret engine kv having the key *some_key*

```shell
$ kapitan secrets --write vault:path/to/secret -f somefile.txt
```

or ` password: ?{vault:path/to/secret}` can be used in file to retrieve keys.
when this part is compiled, it will look same with no change in password's value.

Only the user with the requred tokens/permissions can reveal the compiled keys. Using the command:
```shell
$ kapitan secrets --reveal -f compiled/sometarget/manifests/main.yml

password: some_values_in_somefile
```
## Dependencies

- [hvac](https://github.com/hvac/hvac) is a python client for Hashicorp Vault
