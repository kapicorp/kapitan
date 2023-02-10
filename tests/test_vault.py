#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"vault secrets tests"

import os
import shutil
import tempfile
import unittest
import socket
from contextlib import closing
from time import sleep

import docker
import hvac
from kapitan.refs.base import RefController, Revealer, RefParams
from kapitan.refs.secrets.vaultkv import VaultSecret, VaultError, vault_obj


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


DOCKER_PORT = find_free_port()

# Create temporary folder
REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)

# Create Vault docker container
client = docker.from_env()
env = {
    "VAULT_LOCAL_CONFIG": '{"backend": {"file": {"path": "/vault/file"}}, "listener":{"tcp":{"address":"0.0.0.0:8200","tls_disable":"true"}}}'
}

vault_container = client.containers.run(
    image="vault",
    cap_add=["IPC_LOCK"],
    ports={"8200": DOCKER_PORT},
    environment=env,
    detach=True,
    remove=True,
    command="server",
)


class VaultSecretTest(unittest.TestCase):
    "Test Vault Secret"

    @classmethod
    def setUpClass(cls):
        # make sure the container is up & running before testing
        while vault_container.status != "running":
            sleep(2)
            vault_container.reload()

        # Initialize vault, unseal, mount secret engine & add auth
        os.environ["VAULT_ADDR"] = f"http://127.0.0.1:{DOCKER_PORT}"
        cls.client = hvac.Client()
        init = cls.client.sys.initialize()
        cls.client.sys.submit_unseal_keys(init["keys"])
        os.environ["VAULT_ROOT_TOKEN"] = init["root_token"]
        cls.client.adapter.close()
        cls.client = hvac.Client(token=init["root_token"])
        cls.client.sys.enable_secrets_engine(backend_type="kv-v2", path="secret")
        test_policy = """
        path "secret/*" {
          capabilities = ["read", "list", "create", "update"]
        }
        """
        policy = "test_policy"
        cls.client.sys.create_or_update_policy(name=policy, policy=test_policy)
        os.environ["VAULT_USERNAME"] = "test_user"
        os.environ["VAULT_PASSWORD"] = "test_password"
        cls.client.sys.enable_auth_method("userpass")
        cls.client.create_userpass(username="test_user", password="test_password", policies=[policy])
        cls.client.sys.enable_auth_method("approle")
        cls.client.create_role("test_role")
        os.environ["VAULT_ROLE_ID"] = cls.client.get_role_id("test_role")
        os.environ["VAULT_SECRET_ID"] = cls.client.create_role_secret_id("test_role")["data"]["secret_id"]
        os.environ["VAULT_TOKEN"] = cls.client.create_token(policies=[policy], lease="1h")["auth"][
            "client_token"
        ]

    @classmethod
    def tearDownClass(cls):
        cls.client.adapter.close()
        vault_container.stop()
        client.close()

        shutil.rmtree(REFS_HOME, ignore_errors=True)
        for i in ["ROOT_TOKEN", "TOKEN", "USERNAME", "PASSWORD", "ROLE_ID", "SECRET_ID"]:
            del os.environ["VAULT_" + i]

    def test_token_authentication(self):
        """
        Authenticate using token
        """
        parameters = {"auth": "token"}
        test_client = vault_obj(parameters)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with token failed")
        test_client.adapter.close()

    def test_userpss_authentication(self):
        """
        Authenticate using userpass
        """
        parameters = {"auth": "userpass"}
        test_client = vault_obj(parameters)
        self.assertTrue(test_client.is_authenticated(), msg="Authentication with userpass failed")
        test_client.adapter.close()

    def test_approle_authentication(self):
        """
        Authenticate using approle
        """
        parameters = {"auth": "approle"}
        test_client = vault_obj(parameters)
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
        tag = "?{vaultkv:secret/batman}"
        secret = {"some_key": "some_secret"}
        self.client.secrets.kv.v2.create_or_update_secret(
            path="foo",
            secret=secret,
        )
        env = {"auth": "token"}
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
