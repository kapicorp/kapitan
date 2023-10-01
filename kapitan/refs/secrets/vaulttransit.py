# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"hashicorp vault transit secrets module"

import base64
import logging
from binascii import Error as b_error
from sys import exit

from kapitan import cached
from kapitan.refs.base import RefError
from kapitan.refs.base64 import Base64Ref, Base64RefBackend
from kapitan.refs.vault_resources import VaultClient, VaultError

from hvac.exceptions import Forbidden, InvalidPath

logger = logging.getLogger(__name__)


class VaultTransit(Base64Ref):
    """
    Hashicorp Vault support for Transit Secret Engine
    """

    def __init__(self, data, vault_params, encrypt=True, encode_base64=False, **kwargs):
        """
        Set vault parameter and encoding of data
        """
        self.vault_params = vault_params

        if encrypt:
            self._encrypt(data, self.vault_params.get("crypto_key"), True)
        else:
            self.data = data

        super().__init__(self.data, **kwargs)
        self.type_name = "vaulttransit"

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new VaultSecret from data and ref_params: target_name
        parameters will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs["target_name"]
            if target_name is None:
                raise ValueError("target_name not set")

            target_inv = cached.inv["nodes"].get(target_name, None)
            if target_inv is None:
                raise ValueError("target_inv not set")

            ref_params.kwargs["vault_params"] = target_inv["parameters"]["kapitan"]["secrets"]["vaulttransit"]

            return cls(data, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create VaultSecret: vaulttransit parameters missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False, **kwargs)

    def reveal(self):
        """
        Returns decrypted data
        """
        # can't use super().reveal() as we want bytes
        try:
            ref_data = base64.b64decode(self.data, validate=True)
        except b_error:
            exit("non-alphabet characters in the data")

        return self._decrypt(ref_data)

    def update_key(self, key):
        """
        re-encrypts data with new key, respects original encoding
        returns True if key is different and secret is updated, False otherwise
        """
        if key == self.vault_params.get("crypto_key"):
            return False

        data_dec = self.reveal()

        encode_base64 = self.encoding == "base64"
        if encode_base64:
            logger.info('Content is already base64 encoded "?(vaulttransit:...|base64)" has no effect.')
            data_dec = base64.b64decode(data_dec).decode()
        self._encrypt(data_dec, key, encode_base64)
        self.data = base64.b64encode(self.data).decode()

        return True

    def _encrypt(self, data, key, encode_base64):
        """
        Authenticate with Vault server & returns value of the key from secret

        :returns: secret in plain text
        """
        _data = data
        self.encoding = "original"
        if not encode_base64:
            _data = base64.b64encode(data.encode())
            self.encoding = "base64"
        else:
            # To guarantee _data is bytes
            if isinstance(data, str):
                _data = data.encode()

        client = VaultClient(self.vault_params)
        # token will comprise of two parts path_in_vault:key
        # data = self.data.decode("utf-8").rstrip().split(":")

        try:
            # Request encryption by vault
            response = client.secrets.transit.encrypt_data(
                name=key,
                mount_point=self.vault_params.get("mount", "transit"),
                plaintext=base64.b64encode(_data).decode("ascii"),
            )
            ciphertext = response["data"]["ciphertext"]

            self.data = ciphertext.encode()
            self.vault_params["crypto_key"] = key
        except Forbidden:
            raise VaultError(
                "Permission Denied. "
                + "make sure the token is authorised to access {path} on Vault".format(path=data[0])
            )
        except InvalidPath:
            raise VaultError("{path} does not exist on Vault secret".format(path=data[0]))
        finally:
            client.adapter.close()

    def _decrypt(self, data):
        """
        Authenticate with Vault server & returns value of the key from secret

        :returns: secret in plain text
        """
        client = VaultClient(self.vault_params)
        always_latest = self.vault_params.get("always_latest", True)
        key = self.vault_params.get("crypto_key")
        if key is None:
            raise RefError("Cannot access vault params")

        try:
            if always_latest:
                encrypt_data_response = client.secrets.transit.rewrap_data(
                    name=key,
                    mount_point=self.vault_params.get("mount", "transit"),
                    ciphertext=data.decode(),
                )
                data = encrypt_data_response["data"]["ciphertext"].encode()

            response = client.secrets.transit.decrypt_data(
                name=key,
                mount_point=self.vault_params.get("mount", "transit"),
                ciphertext=data.decode(),
            )
            plaintext = base64.b64decode(response["data"]["plaintext"])

            return plaintext.decode()
        except Forbidden:
            raise VaultError(
                "Permission Denied. "
                + "make sure the token is authorised to access {path} on Vault".format(path=data[0])
            )
        except InvalidPath:
            raise VaultError("{path} does not exist on Vault secret".format(path=data[0]))
        finally:
            client.adapter.close()

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
    def __init__(self, path, ref_type=VaultTransit, **ref_kwargs):
        "init VaultBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "vaulttransit"
