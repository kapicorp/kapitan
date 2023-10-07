# Hashicorp Vault Transit

This feature allows the user to fetch secrets from [Hashicorp Vault](https://www.vaultproject.io/), with the new secret backend keyword 'vaulttransit'.

Author: [@xqp](https://github.com/xqp) [@Moep90](https://github.com/Moep90)

## Specification

The following variables need to be exported to the environment(depending on authentication used) where you will run `kapitan refs --reveal` in order to authenticate to your HashiCorp Vault instance:

* VAULT_ADDR: URL for vault
* VAULT_SKIP_VERIFY=true: if set, do not verify presented TLS certificate before communicating with Vault server. Setting this variable is not recommended except during testing
* VAULT_TOKEN: token for vault or file (~/.vault-tokens)
* VAULT_ROLE_ID: required by approle
* VAULT_SECRET_ID: required by approle
* VAULT_USERNAME: username to login to vault
* VAULT_PASSWORD: password to login to vault
* VAULT_CLIENT_KEY: the path to an unencrypted PEM-encoded private key matching the client certificate
* VAULT_CLIENT_CERT: the path to a PEM-encoded client certificate for TLS authentication to the Vault server
* VAULT_CACERT: the path to a PEM-encoded CA cert file to use to verify the Vault server TLS certificate
* VAULT_CAPATH: the path to a directory of PEM-encoded CA cert files to verify the Vault server TLS certificate
* VAULT_NAMESPACE: specify the Vault Namespace, if you have one

Considering any stringdata like `any.value:whatever-you_may*like` ( in our case let’s encrypt `any.value:whatever-you_may*like` with vault transit ) using the key `2022-02-13-test` in a transit secret engine with mount `mytransit` on the vault server, to use this as a secret either follow:

```shell
echo "any.value:whatever-you_may*like" > somefile.txt
kapitan refs --write vaulttransit:<target_name>/to/secret_inside_kapitan --file somefile.txt --target <target_name>
```

or in a single line

```shell
echo "any.value:whatever-you_may*like"  | kapitan refs --write vaulttransit:<target_name>/to/secret_inside_kapitan -t <target_name> -f -
```

The entire string __"any.value:whatever-you_may*like"__ will be encrypted by vault and looks like this in return: `vault:v2:Jhn3UzthKcJ2s+sEiO60EUiDmuzqUC4mMBWp2Vjg/DGl+GDFEDIPmAQpc5BdIefkplb6yrJZq63xQ9s=`. This then gets base64 encoded and stored in the secret_inside_kapitan. Now secret_inside_kapitan contains the following

```yaml
data: dmF1bHQ6djI6SmhuM1V6dGhLY0oycytzRWlPNjBFVWlEbXV6cVVDNG1NQldwMlZqZy9ER2wrR0RGRURJUG1BUXBjNUJkSWVma3BsYjZ5ckpacTYzeFE5cz0=
encoding: original
type: vaulttransit
vault_params:
  VAULT_ADDR: http://127.0.0.1:8200
  VAULT_SKIP_VERIFY: 'True'
  VAULT_TOKEN: s.i53a1DL83REM61UxlJKLdQDY
  auth: token
  crypto_key: key
  mount: transit
  always_latest: false
```

Encoding tells the type of data given to kapitan, if it is `original` then after decoding base64 we'll get the original secret and if it is `base64` then after decoding once we still have a base64 encoded secret and have to decode again.
Parameters in the secret file are collected from the inventory of the target we gave from CLI `--target my_target`. If target isn't provided then kapitan will identify the variables from the environment, but providing `auth` is necessary as a key inside target parameters like the one shown:

```yaml
parameters:
  kapitan:
    vars:
      target: my_target
      namespace: my_namespace
    secrets:
      vaulttransit:
        VAULT_ADDR: http://vault.example.com:8200
        VAULT_TOKEN: s.i53a1DL83REM61UxlJKLdQDY
        VAULT_SKIP_VERIFY: "True"
        auth: token
        mount: transit
        crypto_key: new_key
        always_latest: False
```

Environment variables that can be defined in kapitan inventory are `VAULT_ADDR`, `VAULT_NAMESPACE`, `VAULT_SKIP_VERIFY`, `VAULT_CLIENT_CERT`, `VAULT_CLIENT_KEY`, `VAULT_CAPATH` & `VAULT_CACERT`.
Extra parameters that can be defined in inventory are:

* `auth`: specify which authentication method to use like `token`,`userpass`,`ldap`,`github` & `approle`
* `mount`: specify the mount point of key's path. e.g if path=`alpha-secret/foo/bar` then `mount: alpha-secret` (default `secret`)
* `crypto_key`: Name of the `encryption key` defined in vault
* `always_latest`: Always rewrap ciphertext to latest rotated `crypto_key` version
Environment variables __should NOT__ be defined in inventory are `VAULT_TOKEN`,`VAULT_USERNAME`,`VAULT_PASSWORD`,`VAULT_ROLE_ID`,`VAULT_SECRET_ID`.
This makes the secret_inside_kapitan file accessible throughout the inventory, where we can use the secret whenever necessary like `?{vaulttransit:${target_name}/secret_inside_kapitan}`

Following is the example file having a secret and pointing to the vault `?{vaulttransit:${target_name}/secret_inside_kapitan}`

```yaml
parameters:
  releases:
    app_version: latest
  app:
    image: app:app-tag
    release: ${releases:app_version}
    replicas: ${replicas}
    args:
      - --verbose=${verbose}
      - --password=?{vaulttransit:${target_name}/secret_inside_kapitan||random:str}
```

when `?{vaulttransit:${target_name}/secret_inside_kapitan}` is compiled, it will look same with an 8 character prefix of sha256 hash added at the end like:

```yaml
kind: Deployment
metadata:
  name: app
  namespace: my_namespace
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - args:
            - --verbose=True
            - --password=?{vaulttransit:${target_name}/secret_inside_kapitan||random:str}
          image: app:app-tag
          name: app
```

Only the user with the required tokens/permissions can reveal the secrets. Please note that the roles and permissions will be handled at the Vault level. We need not worry about it within Kapitan. Use the following command to reveal the secrets:

```shell
kapitan refs --reveal -f compile/file/containing/secret
```

Following is the result of the app-deployment.md file after Kapitan reveal.

```yaml
kind: Deployment
metadata:
  name: app
  namespace: my_namespace
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - args:
            - --verbose=True
            - --password="any.value:whatever-you_may*like"
          image: app:app-tag
          name: app
```

## Vault policies

```hcl
path "mytransit/encrypt/2022-02-13-test" {
    capabilities = [ "create", "update" ]
}

path "mytransit/decrypt/2022-02-13-test" {
    capabilities = [ "create", "update" ]
}
```

## Dependencies

* [hvac](https://github.com/hvac/hvac) is a python client for Hashicorp Vault
