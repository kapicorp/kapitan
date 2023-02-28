# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"hashicorp vault kv secrets module"

import base64
import logging

from kapitan import cached
from kapitan.refs.base import RefError
from kapitan.refs.base64 import Base64Ref, Base64RefBackend
from kapitan.refs.vault_resources import VaultClient, VaultError

from hvac.exceptions import Forbidden, InvalidPath

logger = logging.getLogger(__name__)


class VaultSecret(Base64Ref):
    """
    Hashicorp Vault support for KV Secret Engine
    """

    def __init__(self, data, vault_params, encrypt=True, encode_base64=False, **kwargs):
        """
        Set vault parameter and encoding of data
        data will be passed as bytes
        """
        self.vault_params = vault_params

        if encrypt:
            # not really encryption --> storing key/value in vault
            self.mount = kwargs.get("mount_in_vault")
            self.path = kwargs.get("path_in_vault")
            self.key = kwargs.get("key_in_vault")
            self._encrypt(data, encode_base64)
        else:
            self.data = data

        super().__init__(self.data, **kwargs)
        self.type_name = "vaultkv"

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new VaultSecret from data and ref_params: target_name, token
        parameters will be grabbed from the inventory via target_name
        vault parameters will be read from token
        """

        encoding = ref_params.kwargs.get("encoding", "original")
        if encoding == "original":
            data = data.encode()

        # set vault params as ref params
        if ref_params.kwargs.get("vault_params") is None:
            target_name = ref_params.kwargs["target_name"]
            if target_name is None:
                raise ValueError("target_name not set")

            target_inv = cached.inv["nodes"].get(target_name, None)
            if target_inv is None:
                raise ValueError("target_inv not set")

            try:
                vault_params = target_inv["parameters"]["kapitan"]["secrets"]["vaultkv"]
                ref_params.kwargs["vault_params"] = vault_params
            except KeyError:
                raise RefError("Could not create VaultSecret: vaultkv parameters missing")

        # set mount, path and key as ref params, read from token
        token = ref_params.kwargs.get("token")
        if token is None:
            raise RefError("Could not create VaultSecret: vaultkv parameters missing")

        token_attrs = token.split(":")

        if len(token_attrs) != 5:
            raise RefError("Could not create VaultSecret: ref token is invalid")

        # set mount
        mount = token_attrs[2]
        if not mount:
            mount = vault_params.get("mount", "secret")  # secret is default mount point
        ref_params.kwargs["mount_in_vault"] = mount

        # set path in vault
        path_in_vault = token_attrs[3]
        if not path_in_vault:
            path_in_vault = token_attrs[1]  # ref path in kapitan as default
        ref_params.kwargs["path_in_vault"] = path_in_vault

        # set key
        key = token_attrs[4]
        if key:
            ref_params.kwargs["key_in_vault"] = token_attrs[4]
        else:
            raise RefError("Could not create VaultSecret: vaultkv: key is missing")

        return cls(data, **ref_params.kwargs)

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False, **kwargs)

    def reveal(self):
        """
        Returns decrypted data
        """
        # can't use super().reveal() as we want bytes
        if self.encoding == "base64":
            self.data = self.data.encode()

        return self._decrypt()

    def _encrypt(self, data, encode_base64=False):
        """
        Authenticate with Vault server & write given data in path/key
        """
        if self.path is None:
            raise VaultError(
                "Invalid path: None, you have to specify the path where the secret gets stored (in vault)"
            )

        # get vault client
        client = VaultClient(self.vault_params)
        secrets = {}

        # fetch current secrets from vault
        try:
            if self.vault_params.get("engine") == "kv":
                response = client.secrets.kv.v1.read_secret(
                    path=self.path,
                    mount_point=self.mount,
                )
                secrets = response["data"]
            else:
                response = client.secrets.kv.v2.read_secret_version(
                    path=self.path,
                    mount_point=self.mount,
                )
                secrets = response["data"]["data"]
        except InvalidPath:
            pass  # comes up if vault is empty in specified path

        # append new secret
        secrets[self.key] = data.decode()

        # write updated secrets back to vault
        try:
            client.secrets.kv.v2.create_or_update_secret(
                path=self.path, secret=secrets, mount_point=self.mount
            )
            client.adapter.close()
        except Forbidden:
            raise VaultError(
                "Permission Denied. "
                + "make sure the token is authorised to access '{}' on Vault".format(self.path)
            )

        # set the data to path:key
        data = f"{self.path}:{self.key}".encode()

        self.encoding = "original"
        if encode_base64:
            data = base64.b64encode(data)
            self.encoding = "base64"

        self.data = data

    def _decrypt(self):
        """
        Authenticate with Vault server & returns value of the key from secret

        :returns: secret in plain text
        """
        client = VaultClient(self.vault_params)

        # data is always base64 encoded
        data = base64.b64decode(self.data)

        # token will comprise of two parts, e.g. path/in/vault:key
        data_attrs = data.decode().split(":")
        if len(data_attrs) != 2:
            raise RefError(
                "Invalid vault secret: secret should be stored as 'path/in/vault:key', not '{}'".format(
                    data.decode()
                )
            )
        mount = self.vault_params.get("mount", "secret")
        secret_path = data_attrs[0]
        secret_key = data_attrs[1]

        return_data = ""
        try:
            if self.vault_params.get("engine") == "kv":
                response = client.secrets.kv.v1.read_secret(
                    path=secret_path,
                    mount_point=mount,
                )
                return_data = response["data"][secret_key]
            else:
                response = client.secrets.kv.v2.read_secret_version(
                    path=secret_path,
                    mount_point=mount,
                )
                return_data = response["data"]["data"][secret_key]
            client.adapter.close()
        except Forbidden:
            raise VaultError(
                "Permission Denied. "
                + "make sure the token is authorised to access '{}' on Vault".format(secret_path)
            )
        except InvalidPath:
            raise VaultError("path '{}' does not exist on Vault".format(secret_path))
        except KeyError:
            raise VaultError("key '{}' does not exist on Vault".format(secret_key))
        finally:
            client.adapter.close()

        if return_data == "":
            raise VaultError("'{}' doesn't exist on '{}'".format(secret_key, secret_path))

        if self.encoding == "base64":
            return_data = base64.b64decode(return_data, validate=True).decode()

        return return_data

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {
            "data": self.data,
            "encoding": self.encoding,
            "type": self.type_name,
            "vault_params": self.vault_params,
        }


class VaultBackend(Base64RefBackend):
    def __init__(self, path, ref_type=VaultSecret, **ref_kwargs):
        "init VaultBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "vaultkv"
