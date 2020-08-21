"Azure secrets test"

import os
import tempfile
import unittest
import io
import sys
import contextlib

from kapitan import cached
from kapitan.cli import main
from kapitan.refs.base import RefController, RefParams, Revealer
from kapitan.refs.secrets.azkms import AzureKMSSecret, AzureKMSError

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

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "azkms:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_HOME,
            "--key",
            "mock",
        ]

        main()
        test_tag_content = "revealing: ?{azkms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_HOME]

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual(f"revealing: {test_secret_content}", stdout.getvalue())

        os.remove(test_tag_file)

    def tearDown(self):
        cached.reset_cache()
