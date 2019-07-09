# Hashicorp Vault  
  
This feature allows the user to fetch secrets from [Hashicorp Vault](https://www.vaultproject.io/), an online Kapitan Secret backend `vault`.  
  
Author: [@vaibahvk](https://github.com/vaibhavk) [@daminisatya](https://github.com/daminisatya)  
## Specification  
  
The following variables need to be exported to the environment(depending on authentication used) where you will run `kapitan secrets --reveal` in order to authenticate to your HashiCorp Vault instance:  
* VAULT_ADDR: URL for vault  
* VAULT_SKIP_VERIFY=true: if set, do not verify presented TLS certificate before communicating with Vault server. Setting this variable is not recommended except during testing  
* VAULT_TOKEN: token for vault or file (~/.vault-tokens)  
* VAULT_ROLE_ID: (required by approle)  
* VAULT_SECRET_ID: (required by approle)  
* VAULT_USERNAME: username to login to vault  
* VAULT_PASSWORD: password to login to vault  
* VAULT_CLIENT_KEY: the path to an unencrypted PEM-encoded private key matching the client certificate  
* VAULT_CLIENT_CERT: the path to a PEM-encoded client certificate for TLS authentication to the Vault server  
* VAULT_CACERT: the path to a PEM-encoded CA cert file to use to verify the Vault server TLS certificate  
* VAULT_CAPATH: the path to a directory of PEM-encoded CA cert files to verify the Vault server TLS certificate  
* VAULT_NAMESPACE: specify the Vault Namespace, if you have one  
  
Considering a key-value pair like `my_key`:`my_secret` ( in our case let’s store `hello`:`batman` inside the vault ) in the path `secret/foo` on the vault server, to use this as a secret either follow:  
  
```shell  
$ echo “{'path':'secret/foo','key':'hello'}” > somefile.txt  
$ kapitan secrets --write vault:path/to/secret_inside_kapitan --file somefile.txt --target dev-sea --auth userpass 
```  
or in a single line  
```shell  
$ echo “{'path':'secret/foo','key':'hello'}” | kapitan secrets --write vault:path/to/secret_inside_kapitan -t dev-sea -a userpass -f -  
```  
The entire string __{'path':'secret/foo','key':'hello'}__ is base64 encoded and stored in the secret_inside_kapitan. Now secret_inside_kapitan contains the following  
  
```yaml    
data: 4oCccGF0aDpzZWNlcnQvZm9v4oCdIOKAnGtleTpteV9rZXnigJ0K  
encoding: original  
parameter:
  addr: http://127.0.0.1:8200
  auth: userpass
  client_cert: /path/to/cert
  client_key: /path/to/key
  engine: kv-v2
  mount: team-alpha-secret
  namespace: CICD-alpha
  skip_verify: false
type: vault  
```  
  
Encoding tells the type of data given to kapitan, if it is `original` then after decoding base64 we'll get the original secret and if it is `base64` then after decoding once we still have a base64 encoded secret and have to decode again.  
Parameters in the secret file are collected from the inventory of the target we gave from CLI `--target dev-sea`. If target isn't provided then kapitan will identify the variables from the environment, but providing `auth`(authentication type like token,userpass,github,approle,ldap) is necessary from either CLI (`--auth`) or as a key inside target parameters like the one shown:  
  
```yaml  
parameters:
  kapitan:
    secrets:
      vault:
        auth: userpass
        addr: http://127.0.0.1:8200
        engine: kv-v2
        namespace: CICD-alpha
        mount: team-alpha-secret
        skip_verify: false
        client_key: /path/to/key
        client_cert: /path/to/cert
```
  
Almost all the environment variables can be defined in kapitan inventory except the token, password, secret_id, etc. Environment like `VAULT_TOKEN`,`VAULT_USERNAME`,`VAULT_PASSWORD`,`VAULT_ROLE_ID` and `VAULT_SECRET_ID` need to be defined depending on the authentication type.   
We can use the secret whenever necessary like `?{vault:path/to/secret_inside_kapitan}`.  
  
Following is the example file having a secret and pointing to the vault `?{vault:path/to/secret_inside_kapitan}`  
  
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
    - --password=?{vault:path/to/secret_inside_kapitan}
```  
  
when `?{vault:path/to/secret_inside_kapitan}` is compiled, it will look same with an 8 character prefix of sha256 sum of the content of file(path/to/secret_inside_kapitan) added in the end to make sure secret file wasn't changed since compile like:  
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
            - --password=?{vault:lunadb_ab:57d6f9b7}
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
