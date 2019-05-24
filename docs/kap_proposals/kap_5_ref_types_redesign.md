# Ref Types Redesign

Redesign Kapitan Secrets and rename them as `References` or `Ref`.

This will likely be a breaking change.

Author: @ramaro

## Proposal

Rename `Secrets` into `Ref` (or `References`) to improve consistency and meaning of the backend types
by removing the `ref` backend and introducting new backends:

| Type   | Description | Encrypted? | Compiles To |
| ------ | ----------- |        --- | ----------  |
| gpg    | GnuPG       |        Yes | hashed tag  |
| gkms   | Google KMS  |        Yes | hashed tag  |
| awskms | Amazon KMS  |        Yes | hashed tag  |
| base64 | base64      |        No  | hashed tag  |
| plain  | plain text  |        No  | plain text  |

The type value will now need to be representative of the way a reference is stored via its backend.

A new `plain` backend type is introduced and will compile into revealed state instead of a hashed tag.

A new `base64` backend type will store a base64 encoded value as the backend suggests (replacing the old badly named `ref` backend).


The command line for secrets will be instead:

```shell
$ kapitan refs --write gpg:my/secret1 ...
$ kapitan refs --write base64:my/file ...
$ kapitan refs --write plain:my/info ...
```

### plain backend

The `plain` backend type will allow referring to external state by updating refs programmatically (e.g. in your pipeline)

For example, one can update the value of an environment variable and use `?{plain:my/user}` as a reference in a template:

```shell
$ echo $USER | kapitan refs --write plain:my/user -f -
```

Or update a docker image value as ref `?{plain:images/dev/envoy}`:

```shell
$ echo 'envoyproxy/envoy:v1.10.0' | kapitan refs --write plain:images/dev/envoy -f -
```

These references will be compiled into their values instead of hashed tags.

### base64 backend

The `base64` backend type will function as the original `ref` type.
Except that this time, the name is representative of what is actually happening :)

### Refs path

Refs will be stored by default in the `./refs` path set by `--refs-path` replacing the `--secrets-path` flag.


## Background

### Kapitan Secrets

Kapitan Secrets allow referring to restricted information (passwords, private keys, etc...) in templates while also securely storing them.

On compile, secret tags are updated into hashed tags which validate and instruct `Kapitan` how to reveal tags into decrypted or encoded information.

### Kapitan Secrets example

The following command creates a GPG encrypted secret with the contents of _file.txt_ for recipient `ramaro@google.com` to read:

```shell
$ kapitan secrets --write gpg:my/secret1 -f file.txt --recipients ramaro@google.com
```

This secret can be referred to in a jsonnet compoment:

```json
{
    "type": "app",
    "name": "test_app",
    "username": "user_one",
    "password": "?{gpg:my/secret1}"
}
```

When this compoment is compiled, it looks like (note the hashed tag):

```yaml
type: app
name: test_app
username: user_one
password: ?{gpg:my/secret1:deadbeef}
```

A user with the required permissions can reveal the compiled component:

```shell
$ kapitan secrets --reveal -f compiled/mytarget/manifests/component.yml

type: app
name: test_app
username: user_one
password: secret_content_of_file.txt
```

### Secret Backend Comparison

Kapitan today offers multiple secret backends:

| Type   | Description | Encrypted? | Compiles To |
| ------ | ----------- |        --- | ----------  |
| gpg    | GnuPG       |        Yes | hashed tag  |
| gkms   | Google KMS  |        Yes | hashed tag  |
| awskms | Amazon KMS  |        Yes | hashed tag  |
| ref    | base64      |        No  | hashed tag  |

However, not all backends are encrypted - this is not consistent!

The `ref` type is not encrypted as its purpose is to allow getting started with the Kapitan Secrets workflow without
the need of setting up the encryption backends tooling (gpg, gcloud, boto, etc...)
