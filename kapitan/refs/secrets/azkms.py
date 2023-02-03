"azkms secret module"

import os
import logging
import base64
from urllib.parse import urlparse
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
from azure.keyvault.keys import KeyClient
from azure.identity import DefaultAzureCredential

from kapitan.refs.base64 import Base64Ref, Base64RefBackend
from kapitan.refs.base import RefError
from kapitan import cached
from kapitan.errors import KapitanError

logger = logging.getLogger(__name__)


class AzureKMSError(KapitanError):
    """
    Generic Azure Key Vault error
    """

    pass


def azkms_obj(key_id):
    """
    Return Azure Key Vault Object
    """
    # e.g of key_id https://kapitanbackend.vault.azure.net/keys/myKey/deadbeef
    if not cached.azkms_obj:
        url = urlparse(key_id)
        # ['', 'keys', 'myKey', 'deadbeef'] or ['kapitanbackend.vault.azure.net', 'keys', 'myKey', 'deadbeef']
        # depending on if key_id is prefixed with https://
        attrs = url.path.split("/")
        key_vault_uri = url.hostname or attrs[0]
        key_name = attrs[-2]
        key_version = attrs[-1]

        # If --verbose is set, show requests from azure
        if logger.getEffectiveLevel() > logging.DEBUG:
            logging.getLogger("azure").setLevel(logging.ERROR)
        credential = DefaultAzureCredential()
        key_client = KeyClient(vault_url=f"https://{key_vault_uri}", credential=credential)
        key = key_client.get_key(key_name, key_version)
        cached.azkms_obj = CryptographyClient(key, credential)

    return cached.azkms_obj


class AzureKMSSecret(Base64Ref):
    def __init__(self, data, key, encrypt=True, encode_base64=False, **kwargs):
        """
        encrypts data with key
        set encode_base64 to True to base64 encode data before encrypting and writing
        set encrypt to False if loading data that is already encrypted and base64
        """

        if encrypt:
            self._encrypt(data, key, encode_base64)
            if encode_base64:
                kwargs["encoding"] = "base64"
        else:
            self.data = data
            self.key = key
        super().__init__(self.data, **kwargs)
        self.type_name = "azkms"

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new AzureKMSSecret from data and ref_params: target_name
        key will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs["target_name"]
            if target_name is None:
                raise ValueError("target_name not set")

            target_inv = cached.inv["nodes"].get(target_name, None)
            if target_inv is None:
                raise ValueError("target_inv not set")

            key = target_inv["parameters"]["kapitan"]["secrets"]["azkms"]["key"]
            return cls(data, key, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create AzureKMSSecret: target_name missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False, **kwargs)

    def reveal(self):
        """
        returns decrypted data
        raises AzureKMSError if decryption fails
        """
        # can't use super().reveal() as we want bytes
        ref_data = base64.b64decode(self.data)
        return self._decrypt(ref_data, self.key)

    def update_key(self, key):
        """
        re-encrypts data with new key, respects original encoding
        returns True if key is different and secret is updated, False otherwise
        """
        if key == self.key:
            return False

        data_dec = self.reveal()
        encode_base64 = self.encoding == "base64"
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
                ciphertext = base64.b64encode(_data)
            else:
                request = azkms_obj(key).encrypt(EncryptionAlgorithm.rsa_oaep_256, _data)
                ciphertext = request.ciphertext

            self.data = ciphertext
            self.key = key

        except Exception as e:
            raise AzureKMSError(e)

    def _decrypt(self, data, key):
        """decrypt data"""
        try:
            plaintext = ""
            # Mocking decrypted response for tests
            if self.key == "mock":
                plaintext = "mock".encode()
            else:
                request = azkms_obj(key).decrypt(EncryptionAlgorithm.rsa_oaep_256, data)
                plaintext = request.plaintext

            return plaintext.decode()

        except Exception as e:
            raise AzureKMSError(e)

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding, "key": self.key, "type": self.type_name}


class AzureKMSBackend(Base64RefBackend):
    def __init__(self, path, ref_type=AzureKMSSecret, **ref_kwargs):
        "init AzureKMSBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "azkms"
