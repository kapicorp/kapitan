"Azure secrets test"

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from kapitan import cached
from kapitan.cli import main as kapitan
from kapitan.refs.base import RefController, Revealer
from kapitan.refs.secrets.azkms import AzureKMSSecret, azkms_obj


REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)
REF_CONTROLLER_EMBEDDED = RefController(REFS_HOME, embed_refs=True)
REVEALER_EMBEDDED = Revealer(REF_CONTROLLER_EMBEDDED)


class AzureKMSTest(unittest.TestCase):
    "Test Azure key vault secrets"

    def test_azkms_write_reveal(self):
        """
        Write secret, confirm secret file exists, reveal and compare content
        """
        tag = "?{azkms:secret/test}"
        REF_CONTROLLER[tag] = AzureKMSSecret("mock", "mock")
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/test")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("I am a ?{azkms:secret/test} value")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a mock value", revealed)

    def test_azkms_write_embedded_reveal(self):
        """
        write and compile embedded secret, confirm secret file exists, reveal and compare content"
        """
        tag = "?{azkms:secret/test}"
        REF_CONTROLLER_EMBEDDED[tag] = AzureKMSSecret("mock", "mock")
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/test")))
        ref_obj = REF_CONTROLLER_EMBEDDED[tag]

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write(f"I am a {ref_obj.compile()} value")

        revealed = REVEALER_EMBEDDED.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a mock value", revealed)

    def test_cli_secret_write_reveal_azkms(self):
        """
        run $ kapitan refs --write azkms:test_secret
        and $ kapitan refs --reveal
        using mock key
        """
        test_secret_content = "mock"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        kapitan(
            "refs",
            "--write",
            "azkms:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_HOME,
            "--key",
            "mock",
        )
        test_tag_content = "revealing: ?{azkms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        argv = [
            "refs",
            "--reveal",
            "-f",
            test_tag_file,
            "--refs-path",
            REFS_HOME,
        ]

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            kapitan(*argv)
        self.assertEqual(f"revealing: {test_secret_content}", stdout.getvalue())

        os.remove(test_tag_file)

    def tearDown(self):
        cached.reset_cache()


class AzureKMSClientPerKeyTest(unittest.TestCase):
    "azkms_obj memoizes one client per key_id"

    KEY_A = "https://vault-a.vault.azure.net/keys/keyA/v1"
    KEY_B = "https://vault-b.vault.azure.net/keys/keyB/v2"

    def setUp(self):
        cached.reset_cache()

    def tearDown(self):
        cached.reset_cache()

    @mock.patch("kapitan.refs.secrets.azkms.CryptographyClient")
    @mock.patch("kapitan.refs.secrets.azkms.KeyClient")
    @mock.patch("kapitan.refs.secrets.azkms.DefaultAzureCredential")
    def test_client_per_key_id(self, credential, key_client, crypto_client):
        crypto_client.side_effect = lambda key, cred: mock.Mock()

        client_a = azkms_obj(self.KEY_A)
        client_b = azkms_obj(self.KEY_B)

        self.assertIsNot(client_a, client_b)
        self.assertIs(azkms_obj(self.KEY_A), client_a)
        self.assertIs(azkms_obj(self.KEY_B), client_b)
        self.assertEqual(crypto_client.call_count, 2)
