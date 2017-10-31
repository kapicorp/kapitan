#!/usr/bin/python
#
# Copyright 2017 The Kapitan Authors
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
from kapitan.secrets import secret_gpg_write, secret_gpg_reveal

GPG_HOME = tempfile.mkdtemp()
GPG_OBJ = gnupg.GPG(gnupghome=GPG_HOME)
SECRETS_HOME = tempfile.mkdtemp()
KEY = GPG_OBJ.gen_key(GPG_OBJ.gen_key_input(key_type="RSA",
                                            key_length=2048,
                                            passphrase="testphrase"))
class SecretsTest(unittest.TestCase):
    def test_secret_token_attributes(self):
        "grab attributes and compare to values"
        token_tag = '?{gpg:secret/sauce}'
        _token_tag, token = re.match(SECRET_TOKEN_TAG_PATTERN,
                                     token_tag).groups()
        self.assertEqual(_token_tag, token_tag)
        backend, token_path = secret_token_attributes(token)
        self.assertEqual((backend, token_path), ('gpg', 'secret/sauce'))

    def test_gpg_secret_write_reveal(self):
        "write secret, confirm secret file exists, reveal and compare content"
        token = 'secret/sauce'
        secret_gpg_write(GPG_OBJ, SECRETS_HOME, token, "super secret value",
                         [KEY.fingerprint], passphrase="testphrase")
        self.assertTrue(os.path.isfile(os.path.join(SECRETS_HOME, token)))

        file_with_secret_tags = tempfile.mktemp()
        file_revealed = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce}')
        with open(file_revealed, 'w') as fp:
            secret_gpg_reveal(GPG_OBJ, SECRETS_HOME, file_with_secret_tags,
                              output=fp)
        with open(file_revealed) as fp:
            self.assertEqual("I am a file with a super secret value", fp.read())
