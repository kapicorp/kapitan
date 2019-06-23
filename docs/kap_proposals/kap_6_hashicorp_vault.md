# Hashicorp Vault  
  
This feature allows the user to fetch secrets from [Hashicorp Vault](https://www.vaultproject.io/), an online Kapitan Secret backend `vault` will be introduced.  
  
Author: [@vaibahvk](https://github.com/vaibhavk) [@daminisatya](https://github.com/daminisatya)  
## Specification  
  
The following variables need to be exported to the environment where you run this script in order to authenticate to your HashiCorp Vault instance:  
* VAULT_ADDR: URL for vault  
* VAULT_SKIP_VERIFY=true: if set, do not verify presented TLS certificate before communicating with Vault server. Setting this variable is not recommended except during testing  
* VAULT_AUTHTYPE: authentication type to use: token, userpass, GitHub, LDAP, approle  
* VAULT_TOKEN: token for vault or file (~/.vault-tokens)  
* VAULT_ROLE_ID: (required by approle)  
* VAULT_SECRET_ID: (required by approle)  
* VAULT_USER: username to login to vault  
* VAULT_PASSWORD: password to login to vault  
* VAULT_CLIENT_KEY: the path to an unencrypted PEM-encoded private key matching the client certificate  
* VAULT_CLIENT_CERT: the path to a PEM-encoded client certificate for TLS authentication to the Vault server  
* VAULT_CACERT: the path to a PEM-encoded CA cert file to use to verify the Vault server TLS certificate  
* VAULT_CAPATH: the path to a directory of PEM-encoded CA cert files to verify the Vault server TLS certificate  
* VAULT_NAMESPACE: specify the Vault Namespace, if you have one  
  
Considering a key-value pair like `my_key`:`my_secret` ( in our case let’s store hello:batman inside the vault ) in the path `secret/foo` on the vault server, to use this as a secret either follow:  
  
```shell  
$ echo “{'path':'secret/foo','key':'my_key'}” > somefile.txt  
$ kapitan secrets —write vault:path/to/secret_inside_kapitan -f somefile.txt  
```  
or in a single line  
```shell  
$ echo “{'path':'secrt/foo','key':'my_key'}” | kapitan secrets --write vault:path/to/secret_inside_kapitan -f -  
```  
The entire string __{'path':'secret/foo','key':'my_key'}__ is base64 encoded and stored in the secret_inside_kapitan. Now secret_inside_kapitan contains the following  
  
```  
data: 4oCccGF0aDpzZWNlcnQvZm9v4oCdIOKAnGtleTpteV9rZXnigJ0K  
encoding: original  
type: vault  
```  
  
this makes the secret_inside_kapitan file accessible throughout the inventory, where we can use the secret whenever necessary like `?{vault:path/to/secret_inside_kapitan}`  
  
Following is the example file having a secret and pointing to the vault `?{vault:path/to/secret_inside_kapitan}`  
  
```  
parameters:  
  releases:  
	  cod: latest  
  cod:  
	  image: ?{vault:path/to/secret_inside_kapitan}  
	  release: ${releases:cod}  
	  replicas: ${replicas}  
	  args:  
	  - --verbose=${verbose}  
```  
  
when `?{vault:path/to/secret_inside_kapitan}` is compiled, it will look same with an 8 character prefix of sha256 hash added at the end like:  
```
# Welcome to the README!
Target *dev-sea* is running:
-   1 replicas of *cod* running image ?{vault:targets/secret_inside_kapitan:de0e6a80}
-   on cluster kubernetes
``` 
  
Only the user with the required tokens/permissions can reveal the secrets. Please note that the roles and permissions will be handled at the Vault level. We need not worry about it within Kapitan. Using the command:  

```shell  
$ kapitan secrets --reveal -f compile/file/containing/secret  
```  

Following is the result of the cod.md file after Kapitan reveal.

```  
# Welcome to the README!  
Target *dev-sea* is running:  

-   1 replicas of *cod* running image my_secret
-   on cluster kubernetes

```  

## Dependencies  
 
- [hvac](https://github.com/hvac/hvac) is a python client for Hashicorp Vault
