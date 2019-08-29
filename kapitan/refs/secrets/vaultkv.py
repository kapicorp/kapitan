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

import base64
from binascii import Error as b_error
import hashlib
import re
import os
from sys import argv, exit

import yaml

import hvac
from hvac.exceptions import Forbidden, InvalidPath
from kapitan import cached
from kapitan.errors import KapitanError
from kapitan.resources import inventory
from kapitan.refs.base import Ref, RefBackend, RefError

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader

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
    get_variable = lambda x: parameter.get(x, os.getenv('VAULT_'+x.upper(),default=''))
    env = {}
    env['url'] = get_variable('addr')
    env['namespace'] = get_variable('namespace')
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
    client_key = get_variable('client_key')
    client_cert = get_variable('client_cert') 
    if client_key != '' and client_cert != '':
        env['cert'] = (client_cert,client_key)
    return env

def vault_obj(vault_parameters):
    """
    vault_parameters: necessary parameters to authenticate & get value from vault, provided by inventory
    e.g.:
        addr: http://127.0.0.1:8200
        auth: userpass
        client_cert: /path/to/cert
        client_key: /path/to/key
        namespace: CICD-alpha
        skip_verify: false
    Authenticate client to server and return client object
    """
    env = get_env(vault_parameters)

    client = hvac.Client(
        **{k:v for k,v in env.items() if k not in ('auth', None)}
    )

    auth_type = vault_parameters['auth']
    # GET TOKEN EITHER FROM ENVIRONMENT OF FILE
    if auth_type in ['token','github']:
        env['token'] = os.getenv('VAULT_TOKEN')
        if not env['token']:
            try:
                with open(os.path.join(os.path.expanduser('~'),'.vault-token'),'r') as f:
                    env['token'] = f.read()
            except IOError:
                VaultError("Cannot read file ~/.vault-token")
    # DIFFERENT LOGIN METHOD BASED ON AUTHENTICATION TYPE
    if auth_type == 'token':
        client.token = env['token']
    elif auth_type == 'ldap':
        client.auth.ldap.login(
            username = os.getenv('VAULT_USERNAME'),
            password = os.getenv('VAULT_PASSWORD')
        )
    elif auth_type == 'userpass':
        client.auth_userpass(
            username=os.getenv('VAULT_USERNAME'),
            password=os.getenv('VAULT_PASSWORD')
        )
    elif auth_type == 'approle':
        client.auth_approle(
            os.getenv('VAULT_ROLE_ID'),
            secret_id=os.getenv('VAULT_SECRET_ID')
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
        self.data = data.rstrip()
        self.parameter = kwargs.get('parameter')
        super().__init__(self.data,**kwargs)
        self.type_name = 'vaultkv'

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new VaultSecret from data and ref_params: target_name
        parameters will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs['target_name']
            if target_name is None:
                raise ValueError('target_name not set')

            target_inv = cached.inv['nodes'].get(target_name, None)
            if target_inv is None:
                raise ValueError('target_inv not set')

            ref_params.kwargs['parameter'] = target_inv['parameters']['kapitan']['secrets']['vaultkv']
            return cls(data, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create VaultSecret: vaultkv parameters missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        """
        return a new Ref from file at ref_full_path
        the data key in the file must be base64 encoded
        """
        try:
            with open(ref_full_path) as fp:
                obj = yaml.load(fp, Loader=YamlLoader)
                _kwargs = {key: value for key, value in obj.items() if key not in ('data', 'from_base64')}
                target_inv = inventory(kwargs['search_paths'],kwargs['target_name'])
                if target_inv is None:
                    raise ValueError('target not set')

                _kwargs['parameter'] = target_inv['parameters']['kapitan']['secrets']['vaultkv']
                kwargs.update(_kwargs)
                return cls(obj['data'], from_base64=True, **kwargs)

        except IOError as ex:
            if ex.errno == errno.ENOENT:
                return None

        except KeyError:
            raise VaultError("Could not fetch VaultSecret: vaultkv parameters missing")
            return None

    def reveal(self):
        """
        Returns decrypted data
        """
        # can't use super().reveal() as we want bytes
        try:
            if self.encoding == 'base64':
                self.data = base64.b64decode(self.data, validate=True)

            ref_data = base64.b64decode(self.data, validate=True)
        except b_error:
            exit(
                "non-alphabet characters in the data"
            )

        return self._decrypt(ref_data)

    def _decrypt(self, data):
        """
        Authenticate with Vault server & returns value of the key from secret

        :returns: secret in plain text
        """
        try:
            client = vault_obj(self.parameter)
            # token will comprise of two parts path_in_vault:key
            data = data.decode('utf-8').split(':')
            return_data = ''
            if self.parameter.get('engine') == 'kv':
                response = client.secrets.kv.v1.read_secret(path=data[0],
                                                            mount_point=self.parameter.get('mount','secret'))
                return_data = response['data'][data[1]]
            else:
                response = client.secrets.kv.v2.read_secret_version(path=data[0],
                                                                    mount_point=self.parameter.get('mount','secret'))
                return_data = response['data']['data'][data[1]]
            client.adapter.close()
        except Forbidden:
            VaultError(
                'Permission Denied. '+
                'make sure the token is authorised to access {path} on Vault'.format( path=data[0])
            )
        except InvalidPath:
            VaultError(
                '{path} does not exist on Vault secret'.format(path=data[0])
            )

        if return_data is '':
            VaultError(
                "'{key}' doesn't exist on '{path}'".format(key=data[1], path=data[0])
            )
        return return_data

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding,
                "type": self.type_name}

class VaultBackend(RefBackend):
    def __init__(self, path,target='',search_paths='.', ref_type=VaultSecret):
        "init VaultBackend ref backend type"
        super().__init__(path, ref_type)
        self.type_name = 'vaultkv'
        self.ref_type = ref_type
        self.target = target
        self.search_paths = search_paths

    def __getitem__(self, ref_path):
        # remove the substring notation, if any
        ref_file_path = re.sub(r"(@[\w\.\-\_]+)", "", ref_path)
        full_ref_path = os.path.join(self.path, ref_file_path)
        ref = self.ref_type.from_path(full_ref_path, target_name=self.target,
                                      search_paths=self.search_paths)

        if ref is not None:
            ref.path = ref_path
            ref_path_data = "{}{}".format(ref_file_path, ref.data)
            ref.hash = hashlib.sha256(ref_path_data.encode()).hexdigest()
            ref.token = "{}:{}:{}".format(ref.type_name, ref.path, ref.hash[:8])
            return ref

        raise KeyError(ref_path)
