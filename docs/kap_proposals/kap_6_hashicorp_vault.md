# Hashicorp Vault 

This feature allows user to fetch secrets from [Hashicorp Vault](https://www.vaultproject.io/), an online Kapitan Secret backend `vault` will be introduced. 

Possibly breaking change. 

Author: @vaibhavk

## Specification

Detects Vault information from the environment (i.e. uses VAULT_ADDR, VAULT_ROOT_TOKEN_ID, etc) or file (~/.vault-tokens) whose path can be specified.

The following command creates a secret from _somefile.txt_ using the secret engine kv having the key *some_key*

```shell
$ kapitan secrets --write vault:kv/some_key -f somefile.txt
```

or ` password: ?{vault:kv/some_key}` can be used in file to retrieve keys.
when this part is compiled, it will look same with no change in password's value.

Only the user with the requred tokens/permissions can reveal the compiled keys. Using the command:
```shell
$ kapitan secrets --reveal -f compiled/sometarget/manifests/main.yml

password: some_values_in_somefile
```
## Dependencies

- [hvac](https://github.com/hvac/hvac) is a python client for Hashicorp Vault
- Alternative: [requests](https://pypi.org/project/requests/) to access Vault's REST API directly
