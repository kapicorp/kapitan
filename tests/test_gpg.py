#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"gpg secrets tests"

import os
import tempfile
import unittest

import kapitan.cached as cached
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from kapitan.refs.base import RefController, RefParams, Revealer
from kapitan.refs.secrets.gpg import GPG_KWARGS, GPG_TARGET_FINGERPRINTS, GPGSecret, gpg_obj

# set GNUPGHOME for test_cli
GNUPGHOME = tempfile.mkdtemp()
os.environ["GNUPGHOME"] = GNUPGHOME

gpg_obj(gnupghome=GNUPGHOME)

KEY = cached.gpg_obj.gen_key(
    cached.gpg_obj.gen_key_input(key_type="RSA", key_length=2048, passphrase="testphrase")
)
KEY2 = cached.gpg_obj.gen_key(
    cached.gpg_obj.gen_key_input(key_type="RSA", key_length=2048, passphrase="testphrase")
)
GPG_TARGET_FINGERPRINTS["KEY"] = KEY.fingerprint
GPG_KWARGS["passphrase"] = "testphrase"

REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)
REF_CONTROLLER_EMBEDDED = RefController(REFS_HOME, embed_refs=True)
REVEALER_EMBEDDED = Revealer(REF_CONTROLLER_EMBEDDED)


class GPGSecretsTest(unittest.TestCase):
    "Test GPG secrets"

    def test_gpg_write_reveal(self):
        "write secret, confirm secret file exists, reveal and compare content"
        tag = "?{gpg:secret/sauce}"
        REF_CONTROLLER[tag] = GPGSecret("super secret value", [{"fingerprint": KEY.fingerprint}])
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/sauce")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("I am a file with a ?{gpg:secret/sauce}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a super secret value", revealed)

    def test_gpg_write_embedded_reveal(self):
        "write and compile embedded secret, confirm secret file exists, reveal and compare content"
        tag = "?{gpg:secret/sauce}"
        REF_CONTROLLER_EMBEDDED[tag] = GPGSecret("super secret value", [{"fingerprint": KEY.fingerprint}])
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/sauce")))
        ref_obj = REF_CONTROLLER_EMBEDDED[tag]

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("I am a file with a {}".format(ref_obj.compile()))
        revealed = REVEALER_EMBEDDED.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a super secret value", revealed)

    def test_gpg_base64_write_reveal(self):
        """
        write secret for base64 encoded content, confirm secret file exists,
        reveal and compare content
        """
        tag = "?{gpg:secret/sauce2}"
        REF_CONTROLLER[tag] = GPGSecret(
            "super secret value", [{"fingerprint": KEY.fingerprint}], encode_base64=True
        )
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/sauce2")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("I am a file with a ?{gpg:secret/sauce2}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", revealed)

    def test_gpg_base64_write_embedded_reveal(self):
        """
        write and compile embedded secret for base64 encoded content, confirm secret file exists,
        reveal and compare content
        """
        tag = "?{gpg:secret/sauce2}"
        REF_CONTROLLER_EMBEDDED[tag] = GPGSecret(
            "super secret value", [{"fingerprint": KEY.fingerprint}], encode_base64=True
        )
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/sauce2")))
        ref_obj = REF_CONTROLLER_EMBEDDED[tag]

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("I am a file with a {}".format(ref_obj.compile()))
        revealed = REVEALER_EMBEDDED.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", revealed)

    def test_gpg_function_ed25519(self):
        "write ed25519 (private and public), confirm secret file exists, reveal and check"

        tag = "?{gpg:secret/ed25519||ed25519}"
        REF_CONTROLLER[tag] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/ed25519")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("?{gpg:secret/ed25519}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        try:
            serialization.load_pem_private_key(revealed.encode(), password=None, backend=default_backend())
        except ValueError:
            raise Exception("Failed to decode ed25519 private key")

        REVEALER._reveal_tag_without_subvar.cache_clear()
        tag = "?{gpg:secret/ed25519||ed25519}"
        REF_CONTROLLER[tag] = RefParams()
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)

        try:
            private_key = serialization.load_pem_private_key(
                revealed.encode(), password=None, backend=default_backend()
            )
        except ValueError:
            raise Exception("Failed to decode ed25519 private key")

        # Test 'publickey' with previous private key as the parameter
        tag_ed25519public = "?{gpg:secret/ed25519public||reveal:secret/ed25519|publickey}"
        REF_CONTROLLER[tag_ed25519public] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/ed25519")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("?{gpg:secret/ed25519public}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual(revealed.splitlines()[0], "-----BEGIN PUBLIC KEY-----")

    def test_gpg_function_rsa(self):
        "write rsa (private and public), confirm secret file exists, reveal and check"

        tag = "?{gpg:secret/rsa||rsa}"
        REF_CONTROLLER[tag] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/rsa")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("?{gpg:secret/rsa}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        try:
            serialization.load_pem_private_key(revealed.encode(), password=None, backend=default_backend())
        except ValueError:
            raise Exception("Failed to decode RSA private key")

        REVEALER._reveal_tag_without_subvar.cache_clear()
        # Test with parameter key_size=2048
        tag = "?{gpg:secret/rsa||rsa:2048}"
        REF_CONTROLLER[tag] = RefParams()
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)

        try:
            private_key = serialization.load_pem_private_key(
                revealed.encode(), password=None, backend=default_backend()
            )
        except ValueError:
            raise Exception("Failed to decode RSA private key")

        self.assertEqual(private_key.key_size, 2048)

        # Test rsapublic with previous private key as the parameter
        tag_rsapublic = "?{gpg:secret/rsapublic||reveal:secret/rsa|rsapublic}"
        REF_CONTROLLER[tag_rsapublic] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/rsa")))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("?{gpg:secret/rsapublic}")
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual(revealed.splitlines()[0], "-----BEGIN PUBLIC KEY-----")

    def test_gpg_update_recipients(self):
        """
        update existing base64'd secret with another recipient, confirm content is the same
        """
        tag = "?{gpg:secret/sauce_with_fingerprints}"
        secret = GPGSecret("super secret value", [{"fingerprint": KEY.fingerprint}], encode_base64=True)
        REF_CONTROLLER[tag] = secret
        ref = REF_CONTROLLER[tag]
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, "secret/sauce_with_fingerprints")))
        self.assertTrue(len(ref.recipients), 1)

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, "w") as fp:
            fp.write("I am a file with a ?{gpg:secret/sauce_with_fingerprints}")

        new_recipients = [{"fingerprint": KEY.fingerprint}, {"fingerprint": KEY2.fingerprint}]
        ref.update_recipients(new_recipients)
        ref = REF_CONTROLLER[tag]

        self.assertTrue(len(ref.recipients), 2)
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", revealed)
