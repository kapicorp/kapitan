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

"awskms secrets module"

import base64
import boto3

from kapitan.refs.base import Ref, RefBackend, RefError
from kapitan import cached
from kapitan.errors import KapitanError


class AWSKMSError(KapitanError):
    """Generic AWS KMS errors"""
    pass


def awskms_obj():
    if not cached.awskms_obj:
        cached.awskms_obj = boto3.session.Session().client('kms')
    return cached.awskms_obj


class AWSKMSSecret(Ref):
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
        self.type_name = 'awskms'

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new AWSKMSSecret from data and ref_params: target_name
        key will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs['target_name']
            if target_name is None:
                raise ValueError('target_name not set')

            target_inv = cached.inv['nodes'].get(target_name, None)
            if target_inv is None:
                raise ValueError('target_inv not set')

            key = target_inv['parameters']['kapitan']['secrets']['awskms']['key']
            return cls(data, key, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create AWSKMSSecret: target_name missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False)

    def reveal(self):
        """
        returns decrypted data
        raises AWSKMSError if decryption fails
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
                response = awskms_obj().encrypt(KeyId=key, Plaintext=_data)
                ciphertext = base64.b64encode(response['CiphertextBlob'])
            self.data = ciphertext
            self.key = key

        except Exception as e:
            raise AWSKMSError(e)

    def _decrypt(self, data):
        """decrypt data"""
        try:
            plaintext = ""
            # Mocking decrypted response for tests
            if self.key == "mock":
                plaintext = "mock".encode()
            else:
                response = awskms_obj().decrypt(CiphertextBlob=base64.b64decode(data))
                plaintext = response['Plaintext']

            return plaintext.decode()

        except Exception as e:
            raise AWSKMSError(e)

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding,
                "key": self.key, "type": self.type_name}


class AWSKMSBackend(RefBackend):
    def __init__(self, path, ref_type=AWSKMSSecret):
        "init AWSKMSBackend ref backend type"
        super().__init__(path, ref_type)
        self.type_name = 'awskms'
