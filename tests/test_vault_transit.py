"vault transit tests"

import os
import tempfile
import unittest
import base64

import hvac

# from kapitan.refs import secrets
from kapitan.refs.base import RefController, Revealer
from kapitan.refs.secrets.vaulttransit import VaultTransit

# from kapitan.refs.vault_resources import VaultClient, VaultError
from tests.vault_server import VaultTransitServer
from kapitan.refs.vault_resources import VaultClient


# Create temporary folder
REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)


class VaultTransitTest(unittest.TestCase):
    "Test Vault Transit"

    @classmethod
    def setUpClass(cls):
        # setup vaulttransit server (running in container)
        cls.server = VaultTransitServer(REFS_HOME, "test_vault_transit")
        cls.server.vault_client.secrets.transit.create_key(name="hvac_key")
        cls.server.vault_client.secrets.transit.create_key(name="hvac_updated_key")

        # setup static vault client
        env = {"auth": "token", "crypto_key": "hvac_key"}
        cls.client = VaultClient(env)

    @classmethod
    def tearDownClass(cls):
        # close connections
        cls.client.adapter.close()
        cls.server.close_container()

    def test_vault_transit_enc_data(self):
        """
        Check the encryption works
        """
        env = {"auth": "token", "crypto_key": "hvac_key"}
        file_data = "foo:some_random_value"
        vault_transit_obj = VaultTransit(file_data, env)

        data = base64.b64decode(vault_transit_obj.data.encode())

        response = self.client.secrets.transit.decrypt_data(
            name="hvac_key", mount_point="transit", ciphertext=data.decode()
        )

        plaintext = base64.b64decode(response["data"]["plaintext"])
        file_data_b64 = file_data.encode()
        self.assertTrue(plaintext == file_data_b64, "message")

    def test_vault_transit_dec_data(self):
        """
        Check the decryption works
        """
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

    def test_vault_transit_update_key(self):
        """
        Checks the key update works
        """
        env = {"auth": "token", "crypto_key": "hvac_key", "always_latest": False}
        file_data = "foo:some_random_value"
        vault_transit_obj = VaultTransit(file_data, env)

        data = base64.b64decode(vault_transit_obj.data.encode())

        self.assertTrue(vault_transit_obj.update_key("hvac_updated_key"), "message")
        updated_ciphertext = base64.b64decode(vault_transit_obj.data)
        self.assertNotEqual(data, updated_ciphertext, "message")

        response = self.client.secrets.transit.decrypt_data(
            name="hvac_key", mount_point="transit", ciphertext=data.decode()
        )

        plaintext = base64.b64decode(response["data"]["plaintext"])
        file_data_b64 = file_data.encode()
        self.assertTrue(plaintext == file_data_b64, "message")
