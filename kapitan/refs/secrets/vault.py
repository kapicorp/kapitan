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
from hvac.exceptions import Forbidden, VaultError, InvalidPath
from yaml import safe_load
from os.path import join,expanduser
from os import getenv
from sys import argv, exit

from kapitan.refs.base import Ref, RefBackend, RefError
from kapitan import cached
from kapitan.errors import KapitanError

class VaultError(KapitanError):
    """Generic vault errors"""
    pass

def get_env(parameter):
    """
    The following variables need to be exported to the environment depending on authentication needed
    * VAULT_ADDR: url for vault
    * VAULT_SKIP_VERIFY=true: if set, do not verify presented TLS certificate before communicating with Vault server.
    * VAULT_TOKEN: token for vault
    * VAULT_ROLE_ID: (required by approle)
    * VAULT_SECRET_ID: (required by approle)
    * VAULT_USERNAME: username to login to vault
    * VAULT_PASSWORD: password to login to vault
    * VAULT_CLIENT_KEY: path to an unencrypted PEM-encoded private key matching the client certificate
    * VAULT_CLIENT_CERT: path to a PEM-encoded client certificate for TLS authentication to the Vault server
    * VAULT_CACERT: path to a PEM-encoded CA cert file to use to verify the Vault server TLS certificate
    * VAULT_CAPATH: path to a directory of PEM-encoded CA cert files to verify the Vault server TLS certificate
    * VAULT_NAMESPACE: specify the Vault Namespace, if you have one
    """
    # Helper lambda function to get varibles either from parameters or environment
    get_variable = lambda x: parameter.get(x, getenv('VAULT_'+x.upper(),default=''))
    env = {}
    env['url'] = get_variable('addr')
    env['namespace'] = get_variable('namespace')
    # AUTHENTICATION TYPE
    if parameter.get('auth','token') in ['token','github']:
        env['token'] = getenv('VAULT_TOKEN')
        if not env['token']:
            with open(join(expanduser('~'),'.vault-token'),'r') as f:
                env['token'] = f.read()
    # VERIFY VAULT SERVER TLS CERTIFICATE
    skip_verify = get_variable('skip_verify')
    if skip_verify.lower() == 'false':
        cert = get_variable('cacert')
        if not cert:
            cert_path = get_variable('capath')
            if not cert_path:
                raise Exception('Neither VAULT_CACERT nor VAULT_CAPATH specified')
            env['verify'] = cert_path
        else:
            env['verify'] = cert

    else:
        env['verify'] = False
    # CLIENT CERTIFICATE FOR TLS AUTHENTICATION
    client_key,client_cert = get_variable('client_key'), get_variable('client_cert') 
    if client_key != '' and client_cert != '':
        env['cert'] = (client_cert,client_key)
    return env

def vault_obj(vault_parameters):
    """
    Authenticate client to server and return client object
    """
    env = get_env(vault_parameters)

    client = hvac.Client(
        **{k:v for k,v in env.items() if k not in ('auth', 'token', None)}
    )

    auth_type = vault_parameters['auth']
    if auth_type == 'token':
        client.token = env['token']
    elif auth_type == 'ldap':
        client.auth.ldap.login(
            username = getenv('VAULT_USERNAME'),
            password = getenv('VAULT_PASSWORD')
        )
    elif auth_type == 'userpass':
        client.auth_userpass(
            username=getenv('VAULT_USERNAME'),
            password=getenv('VAULT_PASSWORD')
        )
    elif auth_type == 'approle':
        client.auth_approle(
            getenv('VAULT_ROLE_ID'),
            secret_id=getenv('VAULT_SECRET_ID')
        )
    elif auth_type == 'github':
        client.auth.github.login(token=env['token'])
    else:
        raise "Authentication type '{auth}' not supported".format(auth=auth_type)

    assert (
        client.is_authenticated()
    ), "Vault Authentication Error, Environment Variables defined?"
    return client

class VaultSecret(Ref):
    """
    Hashicorp Vault support for KV Secret Engine
    """

    def __init__(self, data, **kwargs):
        """
        Set vault parameter and encoding of data
        """
        self.encoding = kwargs.get('encoding', 'original')
        self.data = data
        self.parameter = kwargs.get('parameter')
        super().__init__(self.data,**kwargs)
        self.type_name = 'vault'

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new VaultSecret from data and ref_params: target_name
        key will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs['target_name']
            if target_name is None:
                raise ValueError('target_name not set')

            target_inv = cached.inv['nodes'].get(target_name, None)
            if target_inv is None:
                raise ValueError('target_inv not set')

            ref_params.kwargs['parameter'] = target_inv['parameters']['kapitan']['secrets']['vault']
            return cls(data, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create VaultSecret: vault parameters missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False)

    def reveal(self):
        """
        Returns decrypted data
        """
        # can't use super().reveal() as we want bytes
        if self.encoding == 'base64':
            self.data = base64.b64decode(self.data)

        ref_data = base64.b64decode(self.data)
        return self._decrypt(ref_data)

    def _decrypt(self, data):
        """
        Authenticate with Vault server & returns value of the key from secret

        :returns: secret in plain text
        """
        try:
            client = vault_obj(self.parameter)
            data = safe_load(data)
            if self.parameter.get('engine') == 'kv':
                response = client.secrets.kv.v1.read_secret(path=data['path'],
                                                            mount_point=self.parameter.get('mount','secret'))
            else:
                response = client.secrets.kv.v2.read_secret_version(path=data['path'],
                                                                    mount_point=self.parameter.get('mount','secret'))
            client.adapter.close()
        except Forbidden:
            exit(
                'Permission Denied. '+
                'make sure the token is authorised to access {path} on Vault'.format(
                    path=data['path']
                )
            )
        except VaultError as e:
            halt('Vault Error: '+e.message)
        except InvalidPath:
            exit(
                '{path} does not exist on Vault secret'.format(path=data['path'])
            )

        if data['key'] in response['data']:
            return response['data'][data['key']]
        elif data['key'] in response['data']['data']:
            return response['data']['data'][data['key']]
        else:
            exit(
                "'{key}' doesn't exist on '{path}'".format(key=data['key'],
                                                           path=data['path'])
            )

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding,
                "type": self.type_name, "parameter":self.parameter}

class VaultBackend(RefBackend):
    def __init__(self, path, ref_type=VaultSecret):
        "init VaultBackend ref backend type"
        super().__init__(path, ref_type)
        self.type_name = 'vault'
