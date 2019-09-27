# Hashicorp Vault  
  
This feature allows the user to fetch secrets from [Hashicorp Vault](https://www.vaultproject.io/), with the new secret backend keyword 'vaultkv'.  
  
Author: [@vaibahvk](https://github.com/vaibhavk) [@daminisatya](https://github.com/daminisatya)  
## Specification  
  
The following variables need to be exported to the environment(depending on authentication used) where you will run `kapitan secrets --reveal` in order to authenticate to your HashiCorp Vault instance:  
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
  
Considering a key-value pair like `my_key`:`my_secret` ( in our case let’s store `hello`:`batman` inside the vault ) in the path `secret/foo` in a kv-v2(KV version 2) secret engine on the vault server, to use this as a secret either follow:  
  
```shell  
$ echo "foo:hello" > somefile.txt  
$ kapitan secrets --write vaultkv:path/to/secret_inside_kapitan --file somefile.txt --target dev-sea  
```  
or in a single line  
```shell  
$ echo "foo:hello"  | kapitan secrets --write vaultkv:path/to/secret_inside_kapitan -t dev-sea -f -  
```  
The entire string __"foo:hello"__ is base64 encoded and stored in the secret_inside_kapitan. Now secret_inside_kapitan contains the following  
  
```yaml    
data: Zm9vOmhlbGxvCg==  
encoding: original  
type: vaultkv  
vault_params:  
  auth: token
```  
  
Encoding tells the type of data given to kapitan, if it is `original` then after decoding base64 we'll get the original secret and if it is `base64` then after decoding once we still have a base64 encoded secret and have to decode again.  
Parameters in the secret file are collected from the inventory of the target we gave from CLI `--target dev-sea`. If target isn't provided then kapitan will identify the variables from the environment, but providing `auth` is necessary as a key inside target parameters like the one shown:  
```yaml  
parameters:
  kapitan:
    secrets:
      vaultkv:
        auth: userpass
        engine: kv-v2
        mount: team-alpha-secret
        VAULT_ADDR: http://127.0.0.1:8200
        VAULT_NAMESPACE: CICD-alpha
        VAULT_SKIP_VERIFY: false
        VAULT_CLIENT_KEY: /path/to/key
        VAULT_CLIENT_CERT: /path/to/cert
```
Environment variables that can be defined in kapitan inventory are `VAULT_ADDR`, `VAULT_NAMESPACE`, `VAULT_SKIP_VERIFY`, `VAULT_CLIENT_CERT`, `VAULT_CLIENT_KEY`, `VAULT_CAPATH` & `VAULT_CACERT`.  
Extra parameters that can be defined in inventory are:  
* `auth`: specify which authentication method to use like `token`,`userpass`,`ldap`,`github` & `approle`  
* `mount`: specify the mount point of key's path. e.g if path=`alpha-secret/foo/bar` then `mount: alpha-secret` (default `secret`)  
* `engine`: secret engine used, either `kv-v2` or `kv` (default `kv-v2`)  
Environment variables cannot be defined in inventory are `VAULT_TOKEN`,`VAULT_USERNAME`,`VAULT_PASSWORD`,`VAULT_ROLE_ID`,` VAULT_SECRET_ID`.  
This makes the secret_inside_kapitan file accessible throughout the inventory, where we can use the secret whenever necessary like `?{vaultkv:path/to/secret_inside_kapitan}`  
  
Following is the example file having a secret and pointing to the vault `?{vaultkv:path/to/secret_inside_kapitan}`  
  
```yaml
parameters:
  releases:
    cod: latest
  cod:
    image: alledm/cod:${cod:release}
    release: ${releases:cod}
    replicas: ${replicas}
    args:
      - --verbose=${verbose}
      - --password=?{vaultkv:path/to/secret_inside_kapitan}
```  
when `?{vaultkv:path/to/secret_inside_kapitan}` is compiled, it will look same with an 8 character prefix of sha256 hash added at the end like:  
```yaml  
kind: Deployment
metadata:
  name: cod
  namespace: dev-sea
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: cod
    spec:
      containers:
        - args:
            - --verbose=True
            - --password=?{vaultkv:path/to/secret_inside_kapitan:57d6f9b7}
          image: alledm/cod:v2.0.0
          name: cod
``` 
  
Only the user with the required tokens/permissions can reveal the secrets. Please note that the roles and permissions will be handled at the Vault level. We need not worry about it within Kapitan. Use the following command to reveal the secrets:  

```shell  
$ kapitan secrets --reveal -f compile/file/containing/secret 
```  

Following is the result of the cod-deployment.md file after Kapitan reveal.

```yaml  
kind: Deployment
metadata:
  name: cod
  namespace: dev-sea
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: cod
    spec:
      containers:
        - args:
            - --verbose=True
            - --password=batman
          image: alledm/cod:v2.0.0
          name: cod
```  

## Dependencies  
 
- [hvac](https://github.com/hvac/hvac) is a python client for Hashicorp Vault
