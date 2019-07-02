#!/usr/bin/env python3
#
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

"vault secrets tests"

import os
import unittest
import tempfile
import base64

import kapitan.cached as cached
from kapitan.refs.base import RefController, RefParams, Revealer
from kapitan.refs.secrets.vault import  vault_obj, VaultSecret

import hvac


def initialize():
    """
    Initiaize Vault and return root token
    """
    client = hvac.Client()
    init = client.sys.initialize()
    client.sys.submit_unseal_keys(init['keys'])
    return init['root_token']

ROOT_TOKEN= initialize()
print(ROOT_TOKEN)
client = hvac.Client(token = ROOT_TOKEN)
client.sys.enable_secrets_engine(backend_type='kv-v2',path='secret')
test_policy = '''
path "secret/*" {
  capabilities = ["read", "list"]
}
'''
policy = 'test_policy'
client.sys.create_or_update_policy(name=policy,policy=test_policy)
USERNAME = 'test_user'
PASSWORD = 'test_password'
client.sys.enable_auth_method('userpass')
client.create_userpass(username=USERNAME, password=PASSWORD, policies=[ policy ])
client.sys.enable_auth_method('approle')
client.create_role('test_role')
ROLE_ID = client.get_role_id('test_role')
SECRET_ID = client.create_role_secret_id('test_role')['data']['secret_id']
TOKEN = client.create_token(policies=[policy],lease='1h')['auth']['client_token']

REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)


class VaultSecretTest(unittest.TestCase):
    "Test Vault Secret"

    def test_token_authentication(self):
        '''
        Authenticate using token
        '''
        os.environ['VAULT_TOKEN'] = TOKEN
        test_client = vault_obj()
        self.assertTrue(test_client.is_authenticated())
        test_client.adapter.close()

    def test_userpss_authentication(self):
        '''
        Authenticate using userpass
        '''
        os.environ['VAULT_AUTHTYPE'] = 'userpass'
        os.environ['VAULT_USER'] = USERNAME
        os.environ['VAULT_PASSWORD'] = PASSWORD
        test_client = vault_obj()
        self.assertTrue(test_client.is_authenticated())
        test_client.adapter.close()

    def test_approle_authentication(self):
        '''
        Authenticate using approle
        '''
        os.environ['VAULT_AUTHTYPE'] = 'approle'
        os.environ['VAULT_ROLE_ID'] = ROLE_ID
        os.environ['VAULT_SECRET_ID'] = SECRET_ID
        test_client = vault_obj()
        self.assertTrue(test_client.is_authenticated())
        test_client.adapter.close()

    def test_vault_write_reveal(self):
        '''
        Write secret, confirm secret file exists, reveal and compare content
        '''
        tag = '?{vault:secret/batman}'
        secret = { 'some_random_value':'somethin_secret' }
        client.secrets.kv.v2.create_or_update_secret(
            path='foo',
            secret=secret,
        )
        os.environ['VAULT_TOKEN'] = TOKEN
        os.environ['VAULT_AUTHTYPE'] = 'token'
        file_data = "{'path':'foo','key':'some_random_value'}".encode()
        REF_CONTROLLER[tag] = VaultSecret(file_data,encrypt=True,encoding='original')
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME,'secret/batman')))
        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags,'w') as fp:
            fp.write('I am a file with {}'.format(tag))
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual(
            "I am a file with {}".format(secret['some_random_value']), revealed
        )

    def test_vault_base64_write_reveal(self):
        '''
        Write secret, confirm secret file exists, reveal and compare content
        '''
        tag = '?{vault:secret/batwoman}'
        secret = { 'random_value':'something_very_secret' }
        client.secrets.kv.v2.create_or_update_secret(
            path='foo',
            secret=secret,
        )
        os.environ['VAULT_TOKEN'] = TOKEN
        os.environ['VAULT_AUTHTYPE'] = 'token'
        file_data = "{'path':'foo','key':'random_value'}"
        encoded_data = base64.b64encode(file_data.encode())
        REF_CONTROLLER[tag] = VaultSecret(encoded_data,encrypt=True,encoding='base64')
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME,'secret/batwoman')))
        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags,'w') as fp:
            fp.write('I am a file with {}'.format(tag))
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual(
            "I am a file with {}".format(secret['random_value']), revealed
        )
