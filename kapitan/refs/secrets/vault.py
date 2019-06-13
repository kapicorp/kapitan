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

"hashicorp vault secrets module"

import hvac
import base64
from hvac.exceptions import Forbidden, VaultError
from yaml import safe_load
from os.path import join,expanduser
from os import getenv
from sys import argv

from kapitan.refs.base import Ref, RefBackend, RefError
from kapitan import cached
from kapitan.errors import KapitanError

class VaultError(KapitanError):
    """Generic vault errors"""
    pass

def get_env():
    """
    The following variables need to be exported to the environment where you run this script in order to authenticate to your HashiCorp Vault instance:
    * VAULT_ADDR: url for vault
    * VAULT_SKIP_VERIFY=true: if set, do not verify presented TLS certificate before communicating with Vault server. Setting this variable is not recommended except during testing
    * VAULT_AUTHTYPE: authentication type to use: token, userpass, github, ldap, approle
    * VAULT_TOKEN: token for vault
    * VAULT_ROLE_ID: (required by approle)
    * VAULT_SECRET_ID: (required by approle)
    * VAULT_USER: username to login to vault
    * VAULT_PASSWORD: password to login to vault
    * VAULT_CLIENT_KEY: path to an unencrypted PEM-encoded private key matching the client certificate
    * VAULT_CLIENT_CERT: path to a PEM-encoded client certificate for TLS authentication to the Vault server
    * VAULT_CACERT: path to a PEM-encoded CA cert file to use to verify the Vault server TLS certificate
    * VAULT_CAPATH: path to a directory of PEM-encoded CA cert files to verify the Vault server TLS certificate
    * VAULT_NAMESPACE: specify the Vault Namespace, if you have one
    """
    env = {}
    if getenv( 'VAULT_ADDR' ):
        env['url'] = getenv( 'VAULT_ADDR' )
    #   auth_type = os.environ['VAULT_AUTHTYPE']
    #   if auth_type == 'token':
        env['token'] = getenv( 'VAULT_TOKEN' )
        if not env['token']:
            with open(join(expanduser('~'),'.vault-token'),'r') as f:
                env['token'] = f.read()
    return env

def vault_obj():
    client = hvac.Client(
        **{k:v for k,v in get_env().items() if v is not None}
    )
    assert (
        client.is_authenticated()
    ), "Vault Authentication Error, Environment Variables defined?"
    return client


class VaultSecret(Ref):

    """
    Hashicorp Vault can be used if using KV Secret Engine
    """

    def __init__(self,data,encode_base64=False,encrypt=True,**kwargs):
        """
        set encoding_base64 to True to base64 encoding key before encrypting and writing
        """
        if encrypt:
            self._encrypt(data, encode_base64)
        kwargs['encoding'] = self.encoding
        super().__init__(self.data,**kwargs)
        self.type_name = 'vault'

#    @classmethod
#    def from_params(cls, data, ref_params):
#        """
#        Return new GoogleKMSSecret from data and ref_params: target_name
#        key will be grabbed from the inventory via target_name
#        """
#        try:
#            target_name = ref_params.kwargs['target_name']
#            if target_name is None:
#                raise ValueError('target_name not set')
#
#            target_inv = cached.inv['nodes'].get(target_name, None)
#            if target_inv is None:
#                raise ValueError('target_inv not set')
#
#            key = target_inv['parameters']['kapitan']['secrets']['vault']['key']
#            return cls(data, key, **ref_params.kwargs)
#        except KeyError:
#            raise RefError("Could not create GoogleKMSSecret: target_name missing")
#
#    @classmethod
#    def from_path(cls, ref_full_path, **kwargs):
#        return super().from_path(ref_full_path, encrypt=False)

    def _encrypt(self, data,encode_base64):
        """
        encrypt data
        set encode_base64 to True to base64 encode data before writing
        """
        self.encoding = "original"
        if encode_base64:
            self.data = base64.b64encode(data.encode())
            self.encoding = "base64"
        else:
            self.data = data.encode()


    def reveal(self):
        """
        returns decrypted data
        """
        # can't use super().reveal() as we want bytes
        ref_data = base64.b64decode(self.data)
        return self._decrypt(ref_data)

#    def update_key(self, key):
#        """
#        re-encrypts data with new key, respects original encoding
#        returns True if key is different and secret is updated, False otherwise
#        """
#        if key == self.key:
#            return False
#
#        data_dec = self.reveal()
#        encode_base64 = self.encoding == 'base64'
#        if encode_base64:
#            data_dec = base64.b64decode(data_dec).decode()
#        self._encrypt(data_dec, key, encode_base64)
#        self.data = base64.b64encode(self.data).decode()
#        return True

    def _decrypt(self, data):
        """Decrypt data & return value for the key from Vault Server

        :returns: secret in plain text

        """
        try:
            client = vault_obj()
            data = safe_load(data)
            response = client.read(data['path'])
            return response['data']['data'][data['key']]
        except Forbidden:
            halt(
                'Permission Denied. '+
                'make sure the token is authorised to access {} on vault'.format(
                    data['path']
                )
            )
        except VaultError as e:
            halt('Vault Error: '+e.message)


    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding,
                 "type": self.type_name}

class VaultBackend(RefBackend):
    def __init__(self, path, ref_type=VaultSecret):
        "init VaultBackend ref backend type"
        super().__init__(path, ref_type)
        self.type_name = 'vault'
