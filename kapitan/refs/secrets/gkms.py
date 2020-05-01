# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"gkms secrets module"

import base64
import googleapiclient.discovery as gcloud
import logging
import warnings

from kapitan.refs.base64 import Base64Ref, Base64RefBackend
from kapitan.refs.base import RefError
from kapitan import cached
from kapitan.errors import KapitanError

logger = logging.getLogger(__name__)

# Ignore warning from googleapiclient if we are using default credentials
warnings.filterwarnings("ignore", "Your application has authenticated using end user credentials")


class GoogleKMSError(KapitanError):
    """Generic Google KMS errors"""

    pass


def gkms_obj():
    if not cached.gkms_obj:
        # If --verbose is set, show requests from googleapiclient (which are actually logging.INFO)
        if logger.getEffectiveLevel() > logging.DEBUG:
            logging.getLogger("googleapiclient.discovery").setLevel(logging.ERROR)
        kms_client = gcloud.build("cloudkms", "v1", cache_discovery=False)
        cached.gkms_obj = kms_client.projects().locations().keyRings().cryptoKeys()
    return cached.gkms_obj


class GoogleKMSSecret(Base64Ref):
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
        self.type_name = "gkms"

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new GoogleKMSSecret from data and ref_params: target_name
        key will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs["target_name"]
            if target_name is None:
                raise ValueError("target_name not set")

            target_inv = cached.inv["nodes"].get(target_name, None)
            if target_inv is None:
                raise ValueError("target_inv not set")

            key = target_inv["parameters"]["kapitan"]["secrets"]["gkms"]["key"]
            return cls(data, key, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create GoogleKMSSecret: target_name missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False, **kwargs)

    def reveal(self):
        """
        returns decrypted data
        raises GoogleKMSError if decryption fails
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
                ciphertext = base64.b64encode("mock".encode())
            else:
                request = gkms_obj().encrypt(
                    name=key, body={"plaintext": base64.b64encode(_data).decode("ascii")}
                )
                response = request.execute()
                ciphertext = base64.b64decode(response["ciphertext"].encode("ascii"))

            self.data = ciphertext
            self.key = key

        except Exception as e:
            raise GoogleKMSError(e)

    def _decrypt(self, data):
        """decrypt data"""
        try:
            plaintext = ""
            # Mocking decrypted response for tests
            if self.key == "mock":
                plaintext = "mock".encode()
            else:
                request = gkms_obj().decrypt(
                    name=self.key, body={"ciphertext": base64.b64encode(data).decode("ascii")}
                )
                response = request.execute()
                plaintext = base64.b64decode(response["plaintext"].encode("ascii"))

            return plaintext.decode()

        except Exception as e:
            raise GoogleKMSError(e)

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding, "key": self.key, "type": self.type_name}


class GoogleKMSBackend(Base64RefBackend):
    def __init__(self, path, ref_type=GoogleKMSSecret, **ref_kwargs):
        "init GoogleKMSBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "gkms"
