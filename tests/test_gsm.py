"test google secret manager backend"

import unittest
import os
import shutil
import tempfile
import hashlib
from shutil import rmtree

from kapitan.refs.base import RefController, RefParams, Revealer
from kapitan.refs.secrets.gsm import GoogleSMSecret, GoogleSMError
from kapitan import cached
from kapitan.errors import RefHashMismatchError, RefError


REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)
REF_CONTROLLER_EMBEDDED = RefController(REFS_HOME, embed_refs=True)
REVEALER_EMBEDDED = Revealer(REF_CONTROLLER_EMBEDDED)


class GoogleSecretManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["GCP_PROJECT_ID"] = "test"

    def test_gsm_write_reveal(self):
        """
        write secret, confirm it exists, reveal and compare
        """
        tag = "?{gsm:secret/recipe}"
        PROJECT_ID = "test"
        REF_CONTROLLER[tag] = GoogleSMSecret(b"secret ingredient", PROJECT_ID)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/recipe")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("The secret ingredient of the secret ingredient soup is ?{gsm:secret/recipe}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)

        self.assertEqual("The secret ingredient of the secret ingredient soup is nothing", revealed)

    def test_gsm_write_embedded_reveal(self):
        """
        write secret, conform it exists, reveal embedded secret and compare the contents
        """

        tag = "?{gsm:secret/recipe}"
        PROJECT_ID = "test"
        REF_CONTROLLER[tag] = GoogleSMSecret(b"secret ingredient", PROJECT_ID)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/recipe")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            # write secret with default version_id i.e latest
            fp.write("The secret ingredient of the secret ingredient soup is ?{gsm:secret/recipe}")
        revealed = REVEALER_EMBEDDED.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("The secret ingredient of the secret ingredient soup is nothing", revealed)

    def test_gsm_reveal_custom_secret_version(self):
        """
        write secret, confirm it exists, reveal an older version version of the secret and compare
        """

        tag = "?{gsm:secret/recipe}"
        PROJECT_ID = "test"
        REF_CONTROLLER[tag] = GoogleSMSecret(b"secret ingredient", PROJECT_ID)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/recipe")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            # write secret with version_id 1
            fp.write("The secret ingredient of the secret ingredient soup is ?{gsm:secret/recipe:1}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("The secret ingredient of the secret ingredient soup is unknown", revealed)

    def test_gsm_reveal_from_ref_tag(self):
        """
        write secret, confirm it exists, reveal secret of different versions and compare
        """
        tag = "?{gsm:secret/recipe}"
        PROJECT_ID = "test"
        REF_CONTROLLER[tag] = GoogleSMSecret(b"secret ingredient", PROJECT_ID)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/recipe")))

        revealed = REVEALER.reveal_raw_string(tag)
        self.assertEqual("nothing", revealed)

        tag_with_version = "?{gsm:secret/recipe:1}"
        revealed = REVEALER.reveal_raw_string(tag_with_version)
        self.assertEqual("unknown", revealed)

    def test_gsm_with_inputstr(self):
        """
        write secret from inputstr, confirm secret exists, reveal and check
        """

        tag = "?{gsm:secret/recipe||inputstr:secret ingredient}"
        REF_CONTROLLER[tag] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/recipe")))

        # write secret from tag where secret version is specified
        tag_with_version = "?{gsm:another/secret/recipe:2||inputstr:secret ingredient}"
        REF_CONTROLLER[tag_with_version] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "another/secret/recipe")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("The secret ingredient is ?{gsm:secret/recipe}")

        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("The secret ingredient is nothing", revealed)

        rmtree(os.path.join(REFS_HOME, "another"))

    def test_gsm_with_empty_inputstr(self):
        """
        test writing secret from blank inputstring
        """
        tag = "?{gsm:secret/recipe||inputstr}"
        with self.assertRaises(RefError) as error:
            REF_CONTROLLER[tag] = RefParams()

    def test_gsm_reveal_from_token_with_hash(self):
        """
        write secret, confirm it exists, make tag with postfixed hash
        reveal tag with correct hash and incorrect hash and compare
        """
        tag = "?{gsm:secret/recipe}"
        PROJECT_ID = "test"
        REF_CONTROLLER[tag] = GoogleSMSecret(b"secret ingredient", PROJECT_ID)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/recipe")))

        ref_path_data = "{}{}{}".format("secret/recipe", "c2VjcmV0IGluZ3JlZGllbnQ=", "1")
        ref_hash = hashlib.sha256(ref_path_data.encode()).hexdigest()
        tag_with_hash = f"?{{gsm:secret/recipe:1:{ref_hash[:8]}}}"
        revealed = REVEALER.reveal_raw_string(tag_with_hash)
        self.assertEqual("unknown", revealed)

        tag_with_wrong_hash = f"?{{gsm:secret/recipe:latest:{ref_hash[:8]}}}"
        with self.assertRaises(RefHashMismatchError) as error:
            revealed = REVEALER.reveal_raw_string(tag_with_wrong_hash)

    def testDown(self):
        cached.reset_cache()
        if os.path.exists(os.path.join(REFS_HOME, "secret")):
            rmtree(os.path.join(REFS_HOME, "secret"))

    @classmethod
    def tearDownClass(cls):
        os.environ["GCP_PROJECT_ID"] = ""
