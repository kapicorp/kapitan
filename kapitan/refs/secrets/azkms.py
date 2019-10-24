# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"gkms secrets module"

import os
import base64
import logging
import warnings

from kapitan.refs.base64 import Base64Ref, Base64RefBackend
from kapitan.refs.base import RefError
from kapitan import cached
from kapitan.errors import KapitanError

from azure.keyvault.keys import KeyClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
from azure.keyvault.keys.crypto import EncryptionAlgorithm

logger = logging.getLogger(__name__)

# We are using default credentials as defined in the link:
# https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/keyvault/azure-keyvault-keys
# Environment variables for auth
# export AZURE_CLIENT_ID="generated app id"
# export AZURE_CLIENT_SECRET="random password"
# export AZURE_TENANT_ID="tenant id"
# export AZ_VAULT_URL=<vault name>
# export AZ_KEY_NAME=<name of the key used to ecrypt/decrypt
# Remember to set the permissions -
# az keyvault set-policy --name my-key-vault --spn $AZURE_CLIENT_ID --key-permissions get encrypt decrypt


class AzureKMSError(KapitanError):
    """Generic Azure KMS errors"""
    pass


def azkms_obj():
    if not cached.azkms_obj:
        # If --verbose is set, show requests from az api calls (which are actually logging.INFO)
        if logger.getEffectiveLevel() > logging.DEBUG:
            # TODO: set DEBUG for azure.* packages
            logging.setLevel(logging.ERROR)

        assert len(os.environ.get('AZ_VAULT_URL')) != 0, "Please export environment variable AZ_VAULT_URL "
        assert len(os.environ.get('AZ_KEY_NAME')) != 0, "Please export an environment variable AZ_KEY_NAME "

        try:
            _credential = DefaultAzureCredential()
            _key_client = KeyClient(vault_endpoint='ttps://{0}.vault.azure.net'.format(os.environ.get('AZ_VAULT_URL')),
                                        credential=_credential)
            cached.azkms_obj = _key_client.get_cryptography_client(_key_client.get_key(os.environ.get('AZ_KEY_NAME')),
                                                        credentials=_credential)
        except HttpResponseError as he:
            raise AzureKMSError(he)
    return cached.gkms_obj


class AzureKMSSecret(Base64Ref):
    def __init__(self, data, vault, key,
                 encrypt=True,
                 encode_base64=False, **kwargs):
        """
        encrypts data with key, vault defined in inventory
        or picks out environemtn vars AZ_KEY_NAME, AZ_VAULT_URL
        set encode_base64 to True to base64 encode data before encrypting and writing
        set encrypt to False if loading data that is already encrypted and base64
        """
        if encrypt:
            self._encrypt(data, encode_base64)
            if encode_base64:
                kwargs["encoding"] = "base64"
        else:
            self.data = data
            self.key = key if key else os.environ.get('AZ_KEY_NAME')
            self.vault = key if vault else os.environ.get('AZ_VAULT_URL')
        super().__init__(self.data, **kwargs)
        self.type_name = 'azkms'

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new Secret encrypted with a Azure KMS key
        from data and ref_params: target_name
        key will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs['target_name']
            if target_name is None:
                raise ValueError('target_name not set')

            target_inv = cached.inv['nodes'].get(target_name, None)
            if target_inv is None:
                raise ValueError('target_inv not set')

            key = target_inv['parameters']['kapitan']['secrets']['azkms']['key']
            vault = target_inv['parameters']['kapitan']['secrets']['azkms']['vault']
            return cls(data, key, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create AzureKMSSecret: target_name missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False)

    def reveal(self):
        """
        returns decrypted data
        raises AzureKMSError if decryption fails
        """
        # can't use super().reveal() as we want bytes
        ref_data = base64.b64decode(self.data)
        return self._decrypt(ref_data)

    def update_key(self, key):
        """
        re-encrypts data with new key, respects original encoding
        returns True if key is different and secret is updated, False otherwise
        """
        if key == self.key:
            return False

        data_dec = self.reveal()
        encode_base64 = self.encoding == 'base64'
        if encode_base64:
            data_dec = base64.b64decode(data_dec).decode()
        self._encrypt(data_dec, key, encode_base64)
        self.data = base64.b64encode(self.data).decode()
        return True

    def _encrypt(self, data, key, encode_base64):
        """
        encrypts data
        set encode_base64 to True to base64 encode data before writing
        """
        assert isinstance(key, str)
        _data = data
        self.encoding = "original"
        if encode_base64:
            _data = base64.b64encode(data.encode())
            self.encoding = "base64"
        else:
            # To guarantee _data is bytes
            if isinstance(data, str):
                _data = data.encode()
        try:
            ciphertext = ""
            # Mocking encrypted response for tests
            if key == "mock":
                ciphertext = base64.b64encode("mock".encode())
            else:
            #
            # TODO: Get the encryption algo, currently hardcoded to EncryptionAlgorithm.rsa_oaep_256
            #
                _cipher = azkms_obj().encrypt(
                    EncryptionAlgorithm.rsa_oaep_256,
                    base64.b64encode(_data).decode('ascii'))

                ciphertext = base64.b64decode(_cipher.encode('ascii'))

            self.data = ciphertext
            self.key = key

        except Exception as e:
            raise AzureKMSError(e)

    def _decrypt(self, data):
        """decrypt data"""
        try:
            plaintext = ""
            # Mocking decrypted response for tests
            if self.key == "mock":
                plaintext = "mock".encode()
            else:
                _btxt = azkms_obj().decrypt(
                    EncryptionAlgorithm.rsa_oaep_256,
                    base64.b64encode(data).decode('ascii'))

                plaintext = base64.b64decode(_btxt['plaintext'].encode('ascii'))

            return plaintext.decode()

        except Exception as e:
            raise AzureKMSError(e)

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding,
                "key": self.key, "type": self.type_name}


class GoogleKMSBackend(Base64RefBackend):
    def __init__(self, path, ref_type=AzureKMSError):
        "init AzureKMSBackend ref backend type"
        super().__init__(path, ref_type)
        self.type_name = 'azkms'
