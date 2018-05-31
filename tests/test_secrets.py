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
from kapitan.secrets import secret_token_attributes, SECRET_TOKEN_TAG_PATTERN
from kapitan.secrets import secret_gpg_write, secret_gpg_reveal_raw
from kapitan.secrets import secret_gpg_update_recipients, secret_gpg_raw_read_fingerprints

GPG_HOME = tempfile.mkdtemp()
GPG_OBJ = gnupg.GPG(gnupghome=GPG_HOME)
SECRETS_HOME = tempfile.mkdtemp()
KEY = GPG_OBJ.gen_key(GPG_OBJ.gen_key_input(key_type="RSA",
                                            key_length=2048,
                                            passphrase="testphrase"))
KEY2 = GPG_OBJ.gen_key(GPG_OBJ.gen_key_input(key_type="RSA",
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
        secret_gpg_write(GPG_OBJ, SECRETS_HOME, token, "super secret value",
                         False, [{'fingerprint': KEY.fingerprint}],
                         passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(GPG_OBJ, SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            self.assertEqual("I am a file with a super secret value", fp.read())

    def test_gpg_secret_base64_write_reveal(self):
        """
        write secret for base64 encoded content, confirm secret file exists,
        reveal and compare content
        """
        token = 'secret/sauce'
        secret_gpg_write(GPG_OBJ, SECRETS_HOME, token, "super secret value",
                         True, [{'fingerprint': KEY.fingerprint}],
                         passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce:deadbeef}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(GPG_OBJ, SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", fp.read())

    def test_gpg_secret_update_recipients(self):
        """
        update existing secret with another recipient, confirm content is the same
        """
        token = 'secret/sauce'
        secret_gpg_write(GPG_OBJ, SECRETS_HOME, token, "super secret value",
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
        secret_gpg_update_recipients(GPG_OBJ, SECRETS_HOME, token, new_recipients,
                                     passphrase="testphrase")
        self.assertTrue(len(secret_gpg_raw_read_fingerprints(SECRETS_HOME, token)), 2)
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal_raw(GPG_OBJ, SECRETS_HOME, file_with_secret_tags,
                              verify=False, output=fp, passphrase="testphrase")
        with open(file_revealed) as fp:
            self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", fp.read())
