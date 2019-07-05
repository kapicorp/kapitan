#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
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

"gpg secrets tests"

import os
import unittest
import tempfile

import kapitan.cached as cached
from kapitan.refs.base import RefController, RefParams, Revealer
from kapitan.refs.secrets.gpg import gpg_obj, GPGSecret, GPG_KWARGS, GPG_TARGET_FINGERPRINTS

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# set GNUPGHOME for test_cli
GNUPGHOME = tempfile.mkdtemp()
os.environ["GNUPGHOME"] = GNUPGHOME

gpg_obj(gnupghome=GNUPGHOME)

KEY = cached.gpg_obj.gen_key(cached.gpg_obj.gen_key_input(key_type="RSA",
                                                          key_length=2048,
                                                          passphrase="testphrase"))
KEY2 = cached.gpg_obj.gen_key(cached.gpg_obj.gen_key_input(key_type="RSA",
                                                           key_length=2048,
                                                           passphrase="testphrase"))
GPG_TARGET_FINGERPRINTS["KEY"] = KEY.fingerprint
GPG_KWARGS["passphrase"] = "testphrase"

REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)


class GPGSecretsTest(unittest.TestCase):
    "Test GPG secrets"

    def test_gpg_write_reveal(self):
        "write secret, confirm secret file exists, reveal and compare content"
        tag = '?{gpg:secret/sauce}'
        REF_CONTROLLER[tag] = GPGSecret("super secret value", [{'fingerprint': KEY.fingerprint}])
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'secret/sauce')))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce}')
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a super secret value", revealed)

    def test_gpg_base64_write_reveal(self):
        """
        write secret for base64 encoded content, confirm secret file exists,
        reveal and compare content
        """
        tag = '?{gpg:secret/sauce2}'
        REF_CONTROLLER[tag] = GPGSecret("super secret value", [{'fingerprint': KEY.fingerprint}],
                                        encode_base64=True)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'secret/sauce2')))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce2}')
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", revealed)

    def test_gpg_function_rsa(self):
        "write rsa (private and public), confirm secret file exists, reveal and check"

        tag = '?{gpg:secret/rsa|rsa}'
        REF_CONTROLLER[tag] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'secret/rsa')))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('?{gpg:secret/rsa}')
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        try:
            serialization.load_pem_private_key(revealed.encode(), password=None, backend=default_backend())
        except ValueError:
            raise Exception("Failed to decode RSA private key")

        REVEALER._reveal_tag_without_subvar.cache_clear()
        # Test with parameter key_size=2048
        tag = '?{gpg:secret/rsa|rsa:2048}'
        REF_CONTROLLER[tag] = RefParams()
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)

        try:
            private_key = serialization.load_pem_private_key(revealed.encode(), password=None,
                                                             backend=default_backend())
        except ValueError:
            raise Exception("Failed to decode RSA private key")

        self.assertEqual(private_key.key_size, 2048)

        # Test rsapublic with previous private key as the parameter
        tag_rsapublic = '?{gpg:secret/rsapublic|reveal:secret/rsa|rsapublic}'
        REF_CONTROLLER[tag_rsapublic] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'secret/rsa')))

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('?{gpg:secret/rsapublic}')
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual(revealed.splitlines()[0], "-----BEGIN PUBLIC KEY-----")

    def test_gpg_update_recipients(self):
        """
        update existing base64'd secret with another recipient, confirm content is the same
        """
        tag = '?{gpg:secret/sauce_with_fingerprints}'
        secret = GPGSecret("super secret value", [{'fingerprint': KEY.fingerprint}], encode_base64=True)
        REF_CONTROLLER[tag] = secret
        ref = REF_CONTROLLER[tag]
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'secret/sauce_with_fingerprints')))
        self.assertTrue(len(ref.recipients), 1)

        file_with_secret_tags = tempfile.mktemp()
        with open(file_with_secret_tags, 'w') as fp:
            fp.write('I am a file with a ?{gpg:secret/sauce_with_fingerprints}')

        new_recipients = [{'fingerprint': KEY.fingerprint}, {'fingerprint': KEY2.fingerprint}]
        ref.update_recipients(new_recipients)
        ref = REF_CONTROLLER[tag]

        self.assertTrue(len(ref.recipients), 2)
        revealed = REVEALER.reveal_raw_file(file_with_secret_tags)
        self.assertEqual("I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl", revealed)
