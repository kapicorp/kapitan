#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"vault secrets tests"

import os
import tempfile
import unittest
import shutil

from kapitan.refs.base import RefController, Revealer, RefParams
from kapitan.refs.secrets.vaultkv import VaultSecret, VaultClient, VaultError
from tests.vault_server import VaultServer

# Create temporary folder
REFS_PATH = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_PATH)
REVEALER = Revealer(REF_CONTROLLER)


class VaultSecretTest(unittest.TestCase):
    "Test Vault Secret"

    @classmethod
    def setUpClass(cls):
        # setup vault server (running in container)
        cls.server = VaultServer()

    @classmethod
    def tearDownClass(cls):
        # close connection
        cls.server.close_container()
        shutil.rmtree(REFS_PATH, ignore_errors=True)

    def test_token_authentication(self):
        """
        Authenticate using token
        """
        parameters = {"auth": "token"}
        env = dict(**parameters, **self.server.parameters)
        test_client = VaultClient(env)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with token failed")
        test_client.adapter.close()

    def test_userpss_authentication(self):
        """
        Authenticate using userpass
        """
        parameters = {"auth": "userpass"}
        env = dict(**parameters, **self.server.parameters)
        test_client = VaultClient(env)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with userpass failed")
        test_client.adapter.close()

    def test_approle_authentication(self):
        """
        Authenticate using approle
        """
        parameters = {"auth": "approle"}
        env = dict(**parameters, **self.server.parameters)
        test_client = VaultClient(env)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with approle failed")
        test_client.adapter.close()

    def test_vault_write_reveal(self):
        """
        test vaultkv tag with parameters
        """
        parameters = {"auth": "token", "mount": "secret"}
        env = dict(**parameters, **self.server.parameters)
        secret = "bar"

        tag = "?{vaultkv:secret/harleyquinn:secret:testpath:foo}"
        REF_CONTROLLER[tag] = VaultSecret(
            secret.encode(), env, mount_in_vault="secret", path_in_vault="testpath", key_in_vault="foo"
        )

        # confirming ref file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_PATH, "secret/harleyquinn")), msg="Secret file doesn't exist"
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
        parameters = {"auth": "token"}
        env = dict(**parameters, **self.server.parameters)
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
            os.path.isfile(os.path.join(REFS_PATH, "secret/batman")), msg="Secret file doesn't exist"
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
        parameters = {"auth": "token"}
        env = dict(**parameters, **self.server.parameters)
        file_data = "some_not_existing_path:some_key".encode()
        # encrypt false, because we want just reveal
        REF_CONTROLLER[tag] = VaultSecret(file_data, env, encrypt=False)

        # confirming secret file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_PATH, "secret/joker")), msg="Secret file doesn't exist"
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
        parameters = {"auth": "token"}
        env = dict(**parameters, **self.server.parameters)
        # path foo exists from tests before
        file_data = "foo:some_not_existing_key".encode()
        # encrypt false, because we want just reveal
        REF_CONTROLLER[tag] = VaultSecret(file_data, env, encrypt=False)

        # confirming secret file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_PATH, "secret/joker")), msg="Secret file doesn't exist"
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
        parameters = {"auth": "token", "mount": "secret"}
        env = dict(**parameters, **self.server.parameters)
        params = RefParams()
        params.kwargs = {"vault_params": env}

        tag = "?{vaultkv:secret/bane:secret:banes_testpath:banes_testkey||random:int:32}"
        REF_CONTROLLER[tag] = params

        # confirming ref file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_PATH, "secret/bane")), msg="Secret file doesn't exist"
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
        parameters = {"auth": "token", "mount": "secret"}
        env = dict(**parameters, **self.server.parameters)
        params = RefParams()
        params.kwargs = {"vault_params": env}

        tag = "?{vaultkv:secret/robin:secret:robins_testpath:robins_testkey||random:int:32|base64}"
        REF_CONTROLLER[tag] = params

        # confirming ref file exists
        self.assertTrue(
            os.path.isfile(os.path.join(REFS_PATH, "secret/bane")), msg="Secret file doesn't exist"
        )

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("File contents revealed: {}".format(tag))
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        revealed_secret = revealed[24:]

        # confirming secrets are correctly revealed
        self.assertTrue(len(revealed_secret) == 32 and revealed_secret.isnumeric())

    def test_multiple_secrets_in_path(self):
        """
        Write multiple secrets in one path and check if key gets overwritten
        """
        parameters = {"auth": "token", "mount": "secret"}
        env = dict(**parameters, **self.server.parameters)
        params = RefParams()
        params.kwargs = {"vault_params": env}

        # create two secrets that are in the same path in vault
        tag_1 = "?{vaultkv:secret/kv1:secret:same/path:first_key||random:int:32}"  # numeric
        tag_2 = "?{vaultkv:secret/kv2:secret:same/path:second_key||random:loweralpha:32}"  # alphabetic
        REF_CONTROLLER[tag_1] = params
        REF_CONTROLLER[tag_2] = params

        # check if both secrets are still valid
        revealed_1 = REVEALER.reveal_raw_string("File contents revealed: {}".format(tag_1))
        revealed_2 = REVEALER.reveal_raw_string("File contents revealed: {}".format(tag_2))
        revealed_secret_1 = revealed_1[24:]
        revealed_secret_2 = revealed_2[24:]

        # confirming secrets are correctly revealed
        self.assertTrue(revealed_secret_1.isnumeric(), msg="Secret got overwritten")
        self.assertTrue(revealed_secret_2.isalpha(), msg="Secret got overwritten")

        # Advanced: Update one key with another secret
        tag_3 = "?{vaultkv:secret/kv3:secret:same/path:first_key||random:loweralpha:32}"  # updating first key
        REF_CONTROLLER[tag_3] = params

        revealed_3 = REVEALER.reveal_raw_string("File contents revealed: {}".format(tag_3))
        revealed_secret_3 = revealed_3[24:]

        # confirm that secret in first_key is no longer numeric, but alphabetic
        self.assertTrue(revealed_secret_3.isalpha(), msg="Error in updating an existing key")
        self.assertTrue(
            revealed_secret_2.isalpha(), msg="A non accessed key changed by accessing/updating another key"
        )
