"vault transit tests"

import socket
from contextlib import closing
import os
import shutil
import tempfile
import unittest
import base64
from time import sleep

import docker
import hvac
from kapitan.refs import secrets
from kapitan.refs.base import RefController, Revealer
from kapitan.refs.secrets.vaulttransit import VaultError, VaultTransit, vault_obj


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
    ports={8200: DOCKER_PORT},
    environment=env,
    detach=True,
    remove=True,
    command="server",
)


class VaultTransitTest(unittest.TestCase):
    "Test Vault Transit"

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
        cls.client.sys.enable_secrets_engine(backend_type="transit", path="transit")
        test_policy = """
        path "transit/encrypt/hvac_key" {
            capabilities = [ "create", "update" ]
        }

        path "transit/decrypt/hvac_key" {
            capabilities = [ "create", "update" ]
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

        cls.client.secrets.transit.create_key(name="hvac_key")

    @classmethod
    def tearDownClass(cls):
        cls.client.adapter.close()
        vault_container.stop()
        client.close()

        shutil.rmtree(REFS_HOME, ignore_errors=True)
        for i in ["ROOT_TOKEN", "TOKEN", "USERNAME", "PASSWORD", "ROLE_ID", "SECRET_ID"]:
            del os.environ["VAULT_" + i]

    def test_vault_transit_enc_data(self):
        """
        Access non existing secret, expect error
        """
        tag = "?{vaulttransit:secret/spiderman}"
        env = {"auth": "token", "crypto_key": "hvac_key"}
        file_data = "foo:some_random_value"
        vault_transit_obj = VaultTransit(file_data, env)

        data = base64.b64decode(vault_transit_obj.data.encode())

        response = self.client.secrets.transit.decrypt_data(
            name="hvac_key", mount_point="transit", ciphertext=data.decode()
        )

        plaintext = base64.b64decode(response["data"]["plaintext"])
        file_data_b64 = base64.b64encode(file_data.encode())
        self.assertTrue(plaintext == file_data_b64, "message")

    def test_vault_transit_dec_data(self):
        """
        Access non existing secret, expect error
        """
        tag = "?{vaulttransit:secret/spiderman}"
        env = {"auth": "token", "crypto_key": "hvac_key", "always_latest": False}
        file_data = "foo:some_random_value"
        vault_transit_obj = VaultTransit(file_data, env)

        b64_file_data = base64.b64encode(file_data.encode())
        response = self.client.secrets.transit.encrypt_data(
            name="hvac_key", mount_point="transit", plaintext=b64_file_data.decode()
        )

        data = response["data"]["ciphertext"].encode()
        dec_data = vault_transit_obj._decrypt(data)
        self.assertTrue(dec_data == file_data, "message")
