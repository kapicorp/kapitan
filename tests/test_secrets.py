#!/usr/bin/env python3.6
#
# Copyright 2018 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"secrets tests"

import os
import unittest
import re
import tempfile
import gnupg
import base64
from kapitan.secrets import secret_token_attributes, SECRET_TOKEN_TAG_PATTERN
from kapitan.secrets import secret_gpg_write, secret_gpg_reveal_raw, secret_gpg_write_function
from kapitan.secrets import secret_gpg_update_recipients, secret_gpg_raw_read_fingerprints
from kapitan.utils import get_entropy
import kapitan.cached as cached

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

cached.gpg_backend = gnupg.GPG(gnupghome=tempfile.mkdtemp())
SECRETS_HOME = tempfile.mkdtemp()
KEY = cached.gpg_backend.gen_key(cached.gpg_backend.gen_key_input(key_type="RSA",
                                            key_length=2048,
                                            passphrase="testphrase"))
KEY2 = cached.gpg_backend.gen_key(cached.gpg_backend.gen_key_input(key_type="RSA",
                                            key_length=2048,
                                            passphrase="testphrase"))


class SecretsTest(unittest.TestCase):
    "Test secrets"

    def test_secret_token_attributes(self):
        "grab attributes and compare to values"
        token_tag = '?{gpg:secret/sauce}'
        _token_tag, token, func = re.match(SECRET_TOKEN_TAG_PATTERN,
                                           token_tag).groups()
        self.assertEqual(_token_tag, token_tag)
        backend, token_path = secret_token_attributes(token)
        self.assertEqual((backend, token_path), ('gpg', 'secret/sauce'))

    def test_gpg_secret_write_reveal(self):
        "write secret, confirm secret file exists, reveal and compare content"
        token = 'secret/sauce'
        secret_gpg_write(SECRETS_HOME, token, "super secret value",
                         False, [{'fingerprint': KEY.fingerprint}],
                         passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            self.assertEqual("I am a file with a super secret value", fp.read())

    def test_gpg_secret_base64_write_reveal(self):
        """
        write secret for base64 encoded content, confirm secret file exists,
        reveal and compare content
        """
        token = 'secret/sauce'
        secret_gpg_write(SECRETS_HOME, token, "super secret value",
                         True, [{'fingerprint': KEY.fingerprint}],
                         passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", fp.read())

    def test_gpg_secret_update_recipients(self):
        """
        update existing secret with another recipient, confirm content is the same
        """
        token = 'secret/sauce'
        secret_gpg_write(SECRETS_HOME, token, "super secret value",
                         True, [{'fingerprint': KEY.fingerprint}],
                         passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))
        self.assertTrue(len(secret_gpg_raw_read_fingerprints(SECRETS_HOME, token)), 1)

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce:deadbeef}')

        new_recipients = [{'fingerprint': KEY.fingerprint},
                          {'fingerprint': KEY2.fingerprint}]
        secret_gpg_update_recipients(SECRETS_HOME, token, new_recipients,
                                     passphrase="testphrase")
        self.assertTrue(len(secret_gpg_raw_read_fingerprints(SECRETS_HOME, token)), 2)
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", fp.read())

    def test_gpg_secret_write_function_randomstr(self):
        "write randomstr to secret, confirm secret file exists, reveal and check"

        token = "secret/randomstr"
        secret_gpg_write_function(SECRETS_HOME, token, '|randomstr', [{'fingerprint': KEY.fingerprint}],
                                  passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('?{gpg:secret/randomstr:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            secret = fp.read()
            self.assertEqual(len(secret), 43)  # default length of token_urlsafe() string is 43
            assert get_entropy(secret) > 4

        # Test with parameter nbytes=16, correlating with string length 22
        secret_gpg_write_function(SECRETS_HOME, token, '|randomstr:16', [{'fingerprint': KEY.fingerprint}],
                                  passphrase="testphrase")

        file_revealed = tempfile.mktemp()
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            secret = fp.read()
            self.assertEqual(len(secret), 22)

    def test_gpg_secret_write_function_rsa(self):
        "write rsa (private and public), confirm secret file exists, reveal and check"

        token = "secret/rsa"
        secret_gpg_write_function(SECRETS_HOME, token, '|rsa', [{'fingerprint': KEY.fingerprint}],
                                  passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('?{gpg:secret/rsa:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            try:
                private_key = serialization.load_pem_private_key(fp.read().encode(), password=None, backend=default_backend())
            except ValueError:
                raise Exception("Failed to decode RSA private key")

        # Test with parameter key_size=2048
        secret_gpg_write_function(SECRETS_HOME, token, '|rsa:2048', [{'fingerprint': KEY.fingerprint}],
                                  passphrase="testphrase")

        file_revealed = tempfile.mktemp()
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            try:
                private_key = serialization.load_pem_private_key(fp.read().encode(), password=None, backend=default_backend())
            except ValueError:
                raise Exception("Failed to decode RSA private key")

            self.assertEqual(private_key.key_size, 2048)

        # Test rsapublic with previous private key as the parameter
        token_rsapublic = 'secret/rsapublic'
        secret_gpg_write_function(SECRETS_HOME, token_rsapublic, '|rsapublic:secret/rsa', [{'fingerprint': KEY.fingerprint}],
                                  passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token_rsapublic)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('?{gpg:secret/rsapublic:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            public_key = fp.read()
            self.assertEqual(public_key.splitlines()[0], "-----BEGIN PUBLIC KEY-----")

    def test_gpg_secret_write_function_base64(self):
        "write randomstr to secret and base64, confirm secret file exists, reveal and check"

        token = "secret/base64"
        secret_gpg_write_function(SECRETS_HOME, token, '|randomstr|base64', [{'fingerprint': KEY.fingerprint}],
                                  passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('?{gpg:secret/base64:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            secret = fp.read()
            # If the following succeeds, we guarantee that secret is base64-encoded
            self.assertEqual(base64.b64encode(base64.b64decode(secret)).decode("UTF-8"), secret)

    def test_gpg_secret_write_function_sha256(self):
        "write randomstr to secret and sha256, confirm secret file exists, reveal and check"

        token = "secret/sha256"
        secret_gpg_write_function(SECRETS_HOME, token, '|randomstr|sha256', [{'fingerprint': KEY.fingerprint}],
                                  passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('?{gpg:secret/sha256:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            secret = fp.read()
            self.assertEqual(len(secret), 64)
            try:
                int(secret, 16)  # sha256 should convert to hex
            except ValueError:
                raise Exception("secret is not sha256 hash")
