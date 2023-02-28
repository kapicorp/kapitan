# :kapitan-logo: **Kapitan References** (formally ***Secrets***)

One of the motivations behing Kapitan's design is that we believe that everything about your setup should be tracked, and Kapitan takes this to the extreme. Sometimes, however, we have to manage values that we do not think they belong to the **Inventory**: perhaps they are either too variable (for instance, a *Git commit sha* that changes with every build) or too sensitive, like a password or a generic secret, and then they should always be encrypted.

Kapitan has a built in support for **References**, which you can use to manage both these use cases.

**Kapitan References** supports the following backends:

| Backend        | Description                                                | Encrypted        |
|----------------|------------------------------------------------------------|------------------|
| `plain`        | Plain text, (e.g. commit sha)                              | :material-close: |
| `base64`       | Base64, non confidential but with base64 encoding          | :material-close: |
| `gpg`          | Support for <https://gnupg.org/>                           | :material-check: |
| `gkms`         | GCP KMS                                                    | :material-check: |
| `awskms`       | AWS KMS                                                    | :material-check: |
| `azkms`        | Azure Key Vault                                            | :material-check: |
| `env`          | Environment                                                | :material-check: |
| `vaultkv`      | Hashicorp Vault (RO)                                       | :material-check: |
| `vaulttransit` | Hashicorp Vault (encrypt, decrypt, update_key, rotate_key) | :material-check: |


## Setup

Some reference backends require configuration, both in the Inventory and to configure the actual backend.

!!! tip "**Get started**"
    If you want to get started with references but don't want to deal with the initial setup, you can use the `plain` and `base64` reference types. These are great for demos, but we will see they are extremely helpful even in Production environments.
    
    !!! danger
        Both `plain` and `base64` references do not support encryption: they are intended for development or demo purposes only.
        *DO NOT* use `plain` or `base64` for storing sensitive information!

!!! info "**Backend configuration**"

    Configuration for each backend varies, and it is perfomed by configuring the inventory under `parameters.kapitan.secrets`.

    === "plain"
        !!! note "No configuration needed"

    === "base64"
        !!! note "No configuration needed"

    === "gpg"
        ```yaml
        parameters:
          kapitan:
            secrets:
              gpg:
                recipients:
                  - name: example@kapitan.dev
                    fingerprint: D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C
        ```
    === "gkms"
        ```yaml
        parameters:
          kapitan:
            secrets:
              gkms:
                key: 'projects/<project>/locations/<location>/keyRings/<keyRing>/cryptoKeys/<key>'
        ```
    === "awskms"
        ```yaml
        parameters:
          kapitan:
            secrets:
              awskms:
                key: 'alias/nameOfKey'
        ```
    === "azkms"
        ```yaml
        parameters:
          kapitan:
            secrets:
              azkms:
                key: 'https://<keyvault-name>.vault.azure.net/keys/<object-name>/<object-version>'
        ```
    === "env"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{env:targets/${target_name}/mysql/root_password}
          ...
        ```
    === "vaultkv"
        ```yaml
        parameters:
          kapitan:
            secrets:
              vaultkv:
                VAULT_ADDR: http://127.0.0.1:8200
                auth: token
                mount: secret
        ```
    === "vaulttransit"
        ```yaml
        parameters:
          kapitan:
            secrets:
              vaulttransit:
                VAULT_ADDR: https://vault.example.com
                VAULT_TOKEN: s.mqWkI0uB6So0aHH0v0jyDs97
                VAULT_SKIP_VERIFY: "False"  # Recommended
                auth: token
                mount: mytransit
                key: 2022-02-13-test
        ```


!!! tip "Organize your configuration in classes"
    Just like any other inventory parameters, these configurations can be inherited from a common class or defined per target.

    !!! example "`inventory/classes/common.yml`"
        ```yaml
        classes:
        - security.backend
        ...
        ```

    !!! example "`inventory/classes/security/backend.yml`"
        ```yaml
        parameters:
          kapitan:
            secrets:
              <backend>: <configuration>
        ```

??? tip "ADVANCED: Mix-and-Match backends"
    Remember that you can use multiple backends at the same time, and also use variable interpolation for an even greater flexibility. 
    
    In a multi-cloud setup, for instance, you could configure both **GKMS**

    !!! quote "GCP configuration"
        !!! example "`inventory/classes/cloud/gcp.yml`"
            ```yaml
            classes:
            - security.backends.gkms
            ...
            ```

        !!! example "`inventory/classes/security/backends/gkms.yml`"
            ```yaml
            # Configuration for GCP targets
            parameters:
              backend: gkms
              kapitan:
                secrets:
                  gkms: <configuration>
            ```

    !!! quote "AWS configuration"
        !!! example "`inventory/classes/security/backends/awskms.yml`"
            ```yaml
            # Configuration for AWS targets
            parameters:
              backend: awskms
              kapitan:
                secrets:
                  awskms: <configuration>
            ```

        !!! example "`inventory/classes/cloud/aws.yml`"
            ```yaml
            classes:
            - security.backends.awskms
            ...
            ```
    
    Now because they both set the `parameters.backend` variable, you can define a reference whose backend changes based on what class is assigned to the target

    !!! example "`inventory/targets/cloud/gcp/acme.yml`"
        ```yaml
        classes:
        - cloud.aws

        parameters:
          ...
          mysql:
            # the secret backend will change based on the cloud assigned to this target
            root_password: ?{${backend}:targets/${target_name}/mysql/root_password}
          ...
        ```

## Define references

!!! info ""

    References can be defined in the inventory following the syntax ***spaces added for clarity***:

    `?{` **`<backend_id>`** `:` **`<reference_path>`** `}`
    
    ??? tip "expand for advanced features"
        The syntax also supports for **process functions** and **create_functions** which we will discuss later, which brings the full syntax to 

        !!! example ""
            `?{` **`<backend_id>`** `:` **`<reference_path>`** `}` |**`<process_function>`** ||**`<create_function>`**


    === "plain"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{plain:targets/${target_name}/mysql/root_password}
          ...
        ```

        !!! danger "not encrypted"
            This reference type does not support encryption: it is intended for non sensitive data only. *DO NOT* use `plain` for storing sensitive information!

    === "base64" 
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{base64:targets/${target_name}/mysql/root_password}
          ...
        ```
        !!! danger "not encrypted"
            This reference type does not support encryption: it is intended for non sensitive data only. *DO NOT* use `base64` for storing sensitive information!
    === "gpg"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{gpg:targets/${target_name}/mysql/root_password}
          ...
        ```
    === "gkms"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{gkms:targets/${target_name}/mysql/root_password}
          ...
        ```
    === "awskms"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{awskms:targets/${target_name}/mysql/root_password}
          ...
        ```
    === "azkms"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{azkms:targets/${target_name}/mysql/root_password}
          ...
        ```
    === "env"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{env:targets/${target_name}/mysql/root_password}
          ...
        ```
    === "vaultkv"
        read-only
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{vaultkv:targets/${target_name}/mysql/root_password}
          ...
        ```
        read-write:
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{vaultkv:targets/${target_name}/mysql/root_password:mount:path/in/vault:mykey}
          ...
        ```
    === "vaulttransit"
        ```yaml
        parameters:
          ...
          mysql:
            root_password: ?{vaulttransit:targets/${target_name}/mysql/root_password}
          ...
        ```

## Assign a value

### Manually

You can assign values to your reference using the command line. Both reading from a file and pipes are supported.

!!! warning "Please Note"
    **Kapitan** will fail compilation if a reference is not found. Please see how to assign a value [automatically](#automatically) in the next section

!!! info ""
    === "plain"
        ```shell
        kapitan refs --write plain:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write plain:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```
    === "base64"
        ```shell
        kapitan refs --write base64:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write base64:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```
    === "gpg"
        ```shell
        kapitan refs --write gpg:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write gpg:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```
    === "gkms"
        ```shell
        kapitan refs --write gkms:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write gkms:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```
    === "awskms"
        ```shell
        kapitan refs --write vaulttransit:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write vaulttransit:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```
    === "azkms"
        ```shell
        kapitan refs --write azkms:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write azkms:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```
    === "env"

        !!! note "Setting default value only"
            The `env` backend works in a slightly different ways, as it allows you to reference environment variables at runtime.

            For example, for a reference called **`{?env:targets/envs_defaults/mysql_port_${target_name}}`**, **Kapitan** would look for an environment variable called **`KAPITAN_ENV_mysql_port_${TARGET_NAME}`**. 
            
            If that variable cannot be found in the **Kapitan** environment, the default will be taken from the **`refs/targets/envs_defaults/mysql_port_${TARGET_NAME}`** file instead.

        ```shell
        kapitan refs --write env:refs/targets/envs_defaults/mysql_port_${TARGET_NAME} -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write env:refs/targets/envs_defaults/mysql_port_${TARGET_NAME} -t ${TARGET_NAME} -f -
        ```

    === "vaultkv"
        ```shell
        kapitan refs --write vaultkv:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f <input file>
        ```

        which also works with pipes

        ```shell
        cat input_file | kapitan refs --write vaultkv:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```
    === "vaulttransit"

        This backend expects the value to be stored as a `key:value` pair. 

        ```shell
        echo "a_key:a_value" | kapitan refs --write vaulttransit:refs/targets/${TARGET_NAME}/mysql/root_password -t ${TARGET_NAME} -f -
        ```

        When reading from disk, the input file should be formatted accordingly.

### Automatically

Kapitan has built in capabilities to initialise its references on creation, using an elegant combination of primary and secondary functions. This is extremely powerful because it allows for you to make sure they are always initialised with sensible values.

#### primary functions

To automate the creation of the reference, you can add one of the following primary functions to the reference tag by using the syntax `||primary_function:param1:param2`

For instance, to automatically initialise a reference with a ***random string*** with a lenght of 32 characters, you can use the `random` primary function

    ```yaml
    parameters:
      ...
      mysql:
        root_password: ?{${backend}:targets/${target_name}/mysql/root_password||random:str:32}
      ...
    ```

!!! note "Initialise non existent references"
    The first operator here `||` is more similar to a ***logical OR***. 
    
    * If the reference file does not exist, **Kapitan** will use the function to initialise it
    * If the reference file exists, no functions will run.

    !!! tip "Automate secret rotation with ease"
        You can take advantage of it to implement easy rotation of secrets. Simply delete the reference files, and run `kapitan compile`: let **Kapitan** do the rest.

=== "random"

    === "str"
        !!! quote ""
            Generator function for alphanumeric characters, will be url-token-safe
        ```yaml
        ?{${backend}:targets/${target_name}/mysql/root_password||random:str}
        ```

    === "int"
        !!! quote ""
            generator function for digits (0-9)
        ```yaml
        ?{${backend}:targets/${target_name}/mysql/root_password||random:int}
        ```
    === "loweralpha"
        !!! quote ""
            generator function for lowercase letters (a-z)
        ```yaml
        ?{${backend}:targets/${target_name}/mysql/root_password||random:loweralpha}
        ```
    === "upperalpha"
        !!! quote ""
            generator function for uppercase letters (A-Z)
        ```yaml
        ?{${backend}:targets/${target_name}/mysql/root_password||random:upperalpha}
        ```
    === "loweralphanum"
        !!! quote ""
            generator function for lowercase letters and numbers (a-z and 0-9)
        ```yaml
        ?{${backend}:targets/${target_name}/mysql/root_password||random:loweralphanum}
        ```
    === "upperalphanum"
        !!! quote ""
            generator function for uppercase letters and numbers (A-Z and 0-9)
        ```yaml
        ?{${backend}:targets/${target_name}/mysql/root_password||random:upperalphanum}
        ```
    === "special"
        !!! quote ""
            generator function for alphanumeric characters and given special characters
        ```yaml
        ?{${backend}:targets/${target_name}/mysql/root_password||random:special}
        ```
=== "private keys"
    === "rsa"
        !!! quote ""
            Generates an RSA 4096 private key (PKCS#8). You can optionally pass the key size 
        ```yaml
        ?{${backend}:targets/${target_name}/private_key||rsa}
        ```
    === "ed25519"
        !!! quote ""
            Generates a ed25519 private key (PKCS#8)
        ```yaml
        ?{${backend}:targets/${target_name}/private_key||ed25519}
        ```
    === "publickey"
        !!! quote ""
            Derives the public key from a revealed private key
        ```yaml
        ?{${backend}:targets/${target_name}/private_key||rsa}
        ?{${backend}:targets/${target_name}/public_key||reveal:targets/${target_name}/private_key|publickey}
        ```
    === "rsapublic"
        !!! quote ""
            DEPRECATED: use `||publickey`
=== "basicauth"
    !!! quote ""
        Generates a base64 encoded pair of `username:password`
    ```yaml
    ?{${backend}:targets/${target_name}/apache_basicauth||basicauth:username:password}
    ```
=== "reveal"
    !!! quote ""
        Reveals the content of another reference, useful when deriving public keys or a reference requires a different encoding or the same value.
    ```yaml
    ?{${backend}:targets/${target_name}/secret||random:str}
    ?{${backend}:targets/${target_name}/base64_secret||reveal:targets/${target_name}/secret|base64}
    ```
    !!! danger "attention when rotating secrets used with `reveal`"
        If you use reveal to initialise a reference, like `my_reference||reveal:source_reference` the `my_reference` will not be automatically updated if `source_reference` changes.
        Please make sure you also re-initialise `my_reference` correctly

#### secondary functions

=== "base64"
    !!! quote ""
        base64 encodes your reference
    ```yaml
    ?{${backend}:targets/${target_name}/secret||random:str|base64}
    ```
=== "sha256"
    !!! quote ""
        sha256 hashes your reference
        `param1`: `salt`
    ```yaml
    ?{${backend}:targets/${target_name}/secret||random:str|sha256}
    ```

### Reveal references

You can reveal the secrets referenced in the outputs of `kapitan compile` via:

    ```shell
    kapitan refs --reveal -f path/to/rendered/template
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

    ```shell
    kapitan refs --reveal -f compiled/minikube-mysql/manifests/mysql_secret.yml
    ```

This will substitute the referenced secrets with the actual decrypted secrets stored at the referenced paths and display the file content.

You can also use:

    ```shell
    kapitan refs --reveal --ref-file refs/targets/all-glob/mysql/password
    ```

or

    ```shell
    kapitan refs --reveal --tag "?{base64:targets/all-glob/mysql/password}"
    # or
    kapitan refs --reveal --tag "?{base64:targets/all-glob/mysql/password:3192c15c}"
    ```

for more convenience.

## Embedded refs

Please refer to the [CLI reference](/pages/commands/kapitan_compile/#embed-references)

## YAML SubVars References

Kapitan is also able to use access specific keys in YAML content by using subvars.

For instance given a reference `plain:larder` with content:

    ```yaml
    food:
      apples: 1
    ```

I could now have an inventory variable like:

    ```yaml
    parameters:
      number_of_apples: ?{plain:larder@food.apple}
    ```

### Using `subvars` to ingest yaml from command line tools

Subvars can have a very practical use for storing YAML outputs coming straight from other tools. For instance, I could use the GCP `gcloud` command to get all the information about a cluster, and write it into a reference

    ```shell
    gcloud container clusters describe \
      --project ${TARGET_NAME}-project \
      gke-cluster --zone europe-west1 --format yaml \
        | kapitan refs --write plain:clusters/${TARGET_NAME}/cluster -t ${TARGET_NAME} -f -
    ```

knowing the output of `gcloud` to produce yaml that contain the following values:

    ```yaml
    ...
    name: gke-cluster
    releaseChannel:
      channel: REGULAR
    selfLink: https://container.googleapis.com/v1/projects/kapicorp/locations/europe-west1/clusters/gke-cluster
    ...
    ```

I can not reference the link to the cluster in the inventory using:

    ```yaml
    parameters:
      cluster:
        name: ?{plain:clusters/${target_name}/cluster@name} 
        release_channel: ?{plain:clusters/${target_name}/cluster@releaseChannel.channel}
        link: ?{plain:clusters/${target_name}/cluster@selfLink}
    ```

Combined with a Jinja template, I could write automatically documentation containing the details of the clusters I use.

    ```text
    {% set p = inventory.parameters %}
    # Documentation for {{p.target_name}}

    Cluster [{{p.cluster.name}}]({{p.cluster.link}}) has release channel {{p.cluster.release_channel}}
    ```



## Hashicorp Vault

### `vaultkv`

Considering a key-value pair like `my_key`:`my_secret` in the path `secret/foo/bar` in a kv-v2(KV version 2) secret engine on the vault server, to use this as a secret use:

    ```shell
    echo "foo/bar:my_key"  | kapitan refs --write vaultkv:path/to/secret_inside_kapitan -t <target_name> -f -
    ```

To write a secret in the vault with kapitan use a ref tag with following structure:

    ```yaml
    parameters:
      ...
      secret:
        my_secret: ?{vaultkv:targets/${target_name}/mypath:mount:path/in/vault:mykey||<functions>}
      ...
    ```

Leave `mount` empty to use the specified mount from vault params from the inventory (see below). Same applies to the `path/in/vault` where the ref path in kapitan gets taken as default value.  

Parameters in the secret file are collected from the inventory of the target we gave from CLI `-t <target_name>`. If target isn't provided then kapitan will identify the variables from the environment when revealing secret.

Environment variables that can be defined in kapitan inventory are `VAULT_ADDR`, `VAULT_NAMESPACE`, `VAULT_SKIP_VERIFY`, `VAULT_CLIENT_CERT`, `VAULT_CLIENT_KEY`, `VAULT_CAPATH` & `VAULT_CACERT`.
Extra parameters that can be defined in inventory are:

- `auth`: specify which authentication method to use like `token`,`userpass`,`ldap`,`github` & `approle`
- `mount`: specify the mount point of key's path. e.g if path=`alpha-secret/foo/bar` then `mount: alpha-secret` (default `secret`)
- `engine`: secret engine used, either `kv-v2` or `kv` (default `kv-v2`)
Environment variables cannot be defined in inventory are `VAULT_TOKEN`,`VAULT_USERNAME`,`VAULT_PASSWORD`,`VAULT_ROLE_ID`,`VAULT_SECRET_ID`.

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

### `vaulttransit`

Considering a key-value pair like `my_key`:`my_secret` in the path `secret/foo/bar` in a transit secret engine on the vault server, to use this as a secret use:

    ```shell
    echo "any.value:whatever-you_may*like"  | kapitan refs --write vaulttransit:my_target/to/secret_inside_kapitan -t <target_name> -f -
    ```

Parameters in the secret file are collected from the inventory of the target we gave from CLI `-t <target_name>`. If target isn't provided then kapitan will identify the variables from the environment when revealing secret.

Environment variables that can be defined in kapitan inventory are `VAULT_ADDR`, `VAULT_NAMESPACE`, `VAULT_SKIP_VERIFY`, `VAULT_CLIENT_CERT`, `VAULT_CLIENT_KEY`, `VAULT_CAPATH` & `VAULT_CACERT`.
Extra parameters that can be defined in inventory are:

- `auth`: specify which authentication method to use like `token`,`userpass`,`ldap`,`github` & `approle`
- `mount`: specify the mount point of key's path. e.g if path=`my_mount` (default `transit`)
- `crypto_key`: Name of the `encryption key` defined in vault
- `always_latest`: Always rewrap ciphertext to latest rotated crypto_key version
Environment variables cannot be defined in inventory are `VAULT_TOKEN`,`VAULT_USERNAME`,`VAULT_PASSWORD`,`VAULT_ROLE_ID`,`VAULT_SECRET_ID`.

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
      parameters:
        target_name: secrets
        kapitan:
          secrets:
            vaulttransit:
              VAULT_ADDR: http://127.0.0.1:8200
              VAULT_TOKEN: s.i53a1DL83REM61UxlJKLdQDY
              VAULT_SKIP_VERIFY: "True"
              auth: token
              mount: transit
              crypto_key: key
              always_latest: False
      ```

## Azure KMS Secret Backend

To encrypt secrets using keys stored in Azure's Key Vault, a `key_id` is required to identify an Azure key object uniquely.
It should be of the form `https://{keyvault-name}.vault.azure.net/{object-type}/{object-name}/{object-version}`.

### Defining the KMS key

This is done in the inventory under `parameters.kapitan.secrets`.

    ```yaml
    parameters:
      kapitan:
        vars:
          target: ${target_name}
          namespace: ${target_name}
        secrets:
          azkms:
            key: 'https://<keyvault-name>.vault.azure.net/keys/<object-name>/<object-version>'
    ```

The key can also be specified using the `--key` flag

### Creating a secret

Secrets can be created using any of the methods described in the "creating your secret" section.

For example, if the key is defined in the `prod` target file

    ```shell
    echo "my_encrypted_secret" | kapitan refs --write azkms:path/to/secret_inside_kapitan -t prod -f -
    ```

Using the `--key` flag and a `key_id`

    ```shell
    echo "my_encrypted_secret" | kapitan refs --write azkms:path/to/secret_inside_kapitan --key=<key_id> -f -
    ```

### Referencing and revealing a secret

Secrets can be referenced and revealed in any of the ways described above.

For example, to reveal the secret stored at `path/to/secret_inside_kapitan`

    ```shell
    kapitan refs --reveal --tag "?{azkms:path/to/secret_inside_kapitan}"
    ```

*Note:* Cryptographic algorithm used for encryption is *rsa-oaep-256*.
