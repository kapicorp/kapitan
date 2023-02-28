#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"vault secrets tests"

import os
import tempfile
import unittest

from kapitan.refs.base import RefController, Revealer, RefParams
from kapitan.refs.secrets.vaultkv import VaultSecret, VaultClient, VaultError
from tests.vault_server import VaultServer

# Create temporary folder
REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)

<<<<<<< HEAD
# Create Vault docker container
client = docker.from_env()
env = {
    "VAULT_LOCAL_CONFIG": '{"backend": {"file": {"path": "/vault/file"}}, "listener":{"tcp":{"address":"0.0.0.0:8200","tls_disable":"true"}}}'
}

vault_container = client.containers.run(
    image="hashicorp/vault",
    cap_add=["IPC_LOCK"],
    ports={"8200": "8200"},
    environment=env,
    detach=True,
    remove=True,
    command="server",
)

=======
>>>>>>> 2a61fd7 (Merge changes from all three pr's)

class VaultSecretTest(unittest.TestCase):
    "Test Vault Secret"

    @classmethod
    def setUpClass(cls):
        # setup vault server (running in container)
        cls.server = VaultServer(REFS_HOME, "test_vaultkv")

    @classmethod
    def tearDownClass(cls):
        # close connection
        cls.server.close_container()

    def test_token_authentication(self):
        """
        Authenticate using token
        """
        parameters = {"auth": "token"}
        test_client = VaultClient(parameters)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with token failed")
        test_client.adapter.close()

    def test_userpss_authentication(self):
        """
        Authenticate using userpass
        """
        parameters = {"auth": "userpass"}
        test_client = VaultClient(parameters)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with userpass failed")
        test_client.adapter.close()

    def test_approle_authentication(self):
        """
        Authenticate using approle
        """
        parameters = {"auth": "approle"}
        test_client = VaultClient(parameters)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with approle failed")
        test_client.adapter.close()

    def test_vault_write_reveal(self):
        """
        test vaultkv tag with parameters
        """
        env = {"auth": "token", "mount": "secret"}
        secret = "bar"

        tag = "?{vaultkv:secret/harleyquinn:secret:testpath:foo}"
        REF_CONTROLLER[tag] = VaultSecret(
            secret.encode(), env, mount_in_vault="secret", path_in_vault="testpath", key_in_vault="foo"
        )

        # confirming ref file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_HOME, "secret/harleyquinn")), msg="Secret file doesn't exist"
        )

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("File contents revealed: {}".format(tag))
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)

        # confirming secrets are correctly revealed
        self.assertEqual("File contents revealed: {}".format(secret), revealed)

    def test_vault_reveal(self):
        """
        Write secret, confirm secret file exists, reveal and compare content
        """
        # hardcode secret into vault
        env = {"auth": "token"}
        tag = "?{vaultkv:secret/batman}"
        secret = {"some_key": "something_secret"}
        client = VaultClient(env)
        client.secrets.kv.v2.create_or_update_secret(
            path="foo",
            secret=secret,
        )
        client.adapter.close()
        file_data = "foo:some_key".encode()
        # encrypt false, because we want just reveal
        REF_CONTROLLER[tag] = VaultSecret(file_data, env, encrypt=False)

        # confirming secret file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_HOME, "secret/batman")), msg="Secret file doesn't exist"
        )
        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("File contents revealed: {}".format(tag))
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)

        # confirming secrets are correctly revealed
        self.assertEqual("File contents revealed: {}".format(secret["some_key"]), revealed)

    def test_vault_reveal_missing_path(self):
        """
        Access non existing secret, expect error
        """
        tag = "?{vaultkv:secret/joker}"
        env = {"auth": "token"}
        file_data = "some_not_existing_path:some_key".encode()
        # encrypt false, because we want just reveal
        REF_CONTROLLER[tag] = VaultSecret(file_data, env, encrypt=False)

        # confirming secret file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_HOME, "secret/joker")), msg="Secret file doesn't exist"
        )
        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("File contents revealed: {}".format(tag))
        with self.assertRaises(VaultError):
            REVEALER.reveal_raw_file(file_with_secret_tags)

    def test_vault_reveal_missing_key(self):
        """
        Access non existing secret, expect error
        """
        tag = "?{vaultkv:secret/joker}"
        env = {"auth": "token"}
        # path foo exists from tests before
        file_data = "foo:some_not_existing_key".encode()
        # encrypt false, because we want just reveal
        REF_CONTROLLER[tag] = VaultSecret(file_data, env, encrypt=False)

        # confirming secret file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_HOME, "secret/joker")), msg="Secret file doesn't exist"
        )
        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("File contents revealed: {}".format(tag))
        with self.assertRaises(VaultError):
            REVEALER.reveal_raw_file(file_with_secret_tags)

    def test_vault_secret_from_params(self):
        """
        Write secret via token, check if ref file exists
        """
        env = {"vault_params": {"auth": "token", "mount": "secret"}}
        params = RefParams()
        params.kwargs = env

        tag = "?{vaultkv:secret/bane:secret:banes_testpath:banes_testkey||random:int:32}"
        REF_CONTROLLER[tag] = params

        # confirming ref file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_HOME, "secret/bane")), msg="Secret file doesn't exist"
        )

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("File contents revealed: {}".format(tag))
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        revealed_secret = revealed[24:]

        # confirming secrets are correctly revealed
        self.assertTrue(len(revealed_secret) == 32 and revealed_secret.isnumeric())

    def test_vault_secret_from_params_base64(self):
        """
        Write secret via token, check if ref file exists
        """
        env = {"vault_params": {"auth": "token", "mount": "secret"}}
        params = RefParams()
        params.kwargs = env

        tag = "?{vaultkv:secret/robin:secret:robins_testpath:robins_testkey||random:int:32|base64}"
        REF_CONTROLLER[tag] = params

        # confirming ref file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_HOME, "secret/bane")), msg="Secret file doesn't exist"
        )

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("File contents revealed: {}".format(tag))
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        revealed_secret = revealed[24:]

        # confirming secrets are correctly revealed
        self.assertTrue(len(revealed_secret) == 32 and revealed_secret.isnumeric())
