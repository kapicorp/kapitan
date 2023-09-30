"vault transit tests"

import tempfile
import unittest
import base64
import shutil

from kapitan.refs.base import RefController, Revealer
from kapitan.refs.secrets.vaulttransit import VaultTransit
from tests.vault_server import VaultTransitServer
from kapitan.refs.vault_resources import VaultClient


# Create temporary folder
REFS_PATH = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_PATH)
REVEALER = Revealer(REF_CONTROLLER)


class VaultTransitTest(unittest.TestCase):
    "Test Vault Transit"

    @classmethod
    def setUpClass(cls):
        # setup vaulttransit server (running in container)
        cls.server = VaultTransitServer()
        cls.server.vault_client.secrets.transit.create_key(name="hvac_key")
        cls.server.vault_client.secrets.transit.create_key(name="hvac_updated_key")

        # setup static vault client
        parameters = {"auth": "token", "crypto_key": "hvac_key"}
        env = dict(**parameters, **cls.server.parameters)
        cls.client = VaultClient(env)

    @classmethod
    def tearDownClass(cls):
        # close connections
        cls.client.adapter.close()
        cls.server.close_container()
        shutil.rmtree(REFS_PATH, ignore_errors=True)

    def test_vault_transit_enc_data(self):
        """
        Check the encryption works
        """
        parameters = {"auth": "token", "crypto_key": "hvac_key"}
        env = dict(**parameters, **self.server.parameters)

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
        parameters = {"auth": "token", "crypto_key": "hvac_key", "always_latest": False}
        env = dict(**parameters, **self.server.parameters)
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
        parameters = {"auth": "token", "crypto_key": "hvac_key", "always_latest": False}
        env = dict(**parameters, **self.server.parameters)
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
