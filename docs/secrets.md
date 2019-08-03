# Kapitan secrets

Kapitan can manage secrets with the following key management services:

- GPG
- Google Cloud KMS (beta)
- AWS KMS (beta)
- Vault (TBD)

If you want to get started with secrets but don't have a GPG or KMS setup, you can also use the secret `ref` type. Note that `ref` is not encrypted and is intended for development purposes only. *Do not use ref secrets if you're storing sensitive information!*

## Using secrets

The usual flow of creating and using an encrypted secret with kapitan is:

#### 1. Define your GPG recipients or KMS key 

This is done in the inventory under `parameters.kapitan.secrets`. 

Just like any other inventory parameters, this can be inherited from a common class or defined per target. For example, `common.yml` may contain:

```yaml
parameters:
  kapitan:
    vars:
      target: ${target_name}
      namespace: ${target_name}
    secrets:
      gpg:
        recipients:
          - name: example@kapitan.dev
            fingerprint: D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C
      gkms:
        key: 'projects/<project>/locations/<location>/keyRings/<keyRing>/cryptoKeys/<key>'
      awskms:
        key: 'alias/nameOfKey'
```

#### 2. Create your secret

##### Manually via command line:

```shell
$ kapitan secrets --write <secret_type>:path/to/secret/file -t <target_name> -f <secret_file>
```

​	where `<secret_type>` can be any of:

- `ref`: ref type (not encrypted)
- `gpg`: GPG
- `gkms`: Google Cloud KMS
- `awskms`: AWS KMS
- `vault` (TBC)

Kapitan will inherit the secrets configuration for the specified target, and encrypt and save your secret into `<path/to/secret/file>`.

##### Automatically

When referencing your secret in the inventory during compile, you can use the following functions to automatically generate, encrypt and save your secret:

```
randomstr - Generates a random string. You can optionally pass the length you want i.e. `|randomstr:32`
base64 - base64 encodes your secret; to be used as a secondary function i.e. `|randomstr|base64`
sha256 - sha256 hashes your secret; to be used as a secondary function i.e. `|randomstr|sha256`. You can optionally pass a salt i.e `|randomstr|sha256:salt` -> becomes `sha256("salt:<generated random string>")`
reveal - Decrypts a secret; to be used as a secondary function, useful for reuse of a secret like for different encodings i.e `|reveal:path/to/secret|base64`
rsa - Generates an RSA 4096 private key (PKCS#8). You can optionally pass the key size i.e. `|rsa:2048`
rsapublic - Derives an RSA public key from a revealed private key i.e. `|reveal:path/to/encrypted_private_key|rsapublic`
```

*Note*: If you use `|reveal:/path/secret`, when changing the `/path/secret` file make sure you also delete any secrets referencing `/path/secret` so kapitan can regenerate them.

#### 3. Reference your secrets in your classes/targets and run `kapitan compile`

Secrets can be referenced in the format `?{<secret_type>:path/to/secret/file}`.

For example, assume for now that your GPG-encrypted secret is already stored in a file at `targets/secrets/mysql_password`. This can be referenced in the inventory in the following format:

```yaml
users:
  root:
    # If 'secrets/targets/${target_name}/mysql/password' doesn't exist, we can automatically generate a random b64-encoded password as follows
    password: ?{gpg:targets/${target_name}/mysql/password|randomstr|base64}
```

During compile, kapitan will search for the path `targets/${target_name}/mysql/password`. Should it not exist, then it will automatically generate a random base64 password and save it to that path.

#### 4. Reveal and use the secrets

You can reveal the secrets referenced in the outputs of `kapitan compile` via:

```
$ kapitan secrets --reveal -f path/to/rendered/template
```

For example, `compiled/minikube-mysql/manifests/mysql_secret.yml` with the following content:

```yaml
apiVersion: v1
data:
  MYSQL_ROOT_PASSWORD: ?{gpg:targets/minikube-mysql/mysql/password:ec3d54de}
  MYSQL_ROOT_PASSWORD_SHA256: ?{gpg:targets/minikube-mysql/mysql/password_sha256:122d2732}
kind: Secret
metadata:
  annotations: {}
  labels:
    name: example-mysql
  name: example-mysql
  namespace: minikube-mysql
type: Opaque
```

can be revealed as follows:

```
$ kapitan secrets --reveal -f compiled/minikube-mysql/manifests/mysql_secret.yml
```

This will substitute the referenced secrets with the actual decrypted secrets stored at the referenced paths and display the file content.

## Secret sub-variables

As illustrated above, one file corresponds to one secret. It is now possible for users who would like to reduce the decryption overhead to manually create a yaml file that contains multiple secrets, each of which can be referenced by its object key. For example, consider the secret file `secrets/mysql_secrets`:

```yaml
mysql_passwords:
	secret_foo: hello_world
	secret_bar: 54321password
```

This can be manually encrypted by:

```
$ kapitan secrets --write gpg:components/secrets/mysql_secrets -t prod -f secrets/mysql_secrets
```

To reference `secret_foo`inside this file, you can specify it in the inventory as follows:

`secret_foo: ${gpg:components/secrets/mysql_secrets@mysql_passwords.secret_foo}`