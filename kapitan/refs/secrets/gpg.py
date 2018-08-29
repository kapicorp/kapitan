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

"secrets module"

import base64
from collections import defaultdict
import gnupg
import logger
import os
import time

from kapitan.refs.base import Ref, RefBackend
from kapitan import cached


class GPGError(Exception):
    """Generic GPG errors"""
    pass


def gpg_obj():
    if not cached.gpg_obj:
        cached.gpg_obj = gnupg.GPG()
    return cached.gpg_obj


class GPGSecret(Ref):
    def __init__(self, data, recipients, encode_base64=False, from_base64=False, **kwargs):
        """
        encrypts data for recipients
        set encode_base64 to True to base64 encode data before writing
        if fingerprint key is not set in recipients, the first non-expired fingerprint will be used
        if fingerprint is set, there will be no name based lookup
        """
        fingerprints = lookup_fingerprints(recipients)
        self._encrypt(data, fingerprints, encode_base64)  # TODO review if (gpg?) kwargs are really needed
        super().__init__(self.data, from_base64, **kwargs)
        self.type = 'gpg'

    def reveal(self):
        """
        returns decrypted data
        raises GPGError if decryption fails
        """
        self._decrypt(self.data)

    def update_recipients(self, recipients):
        """
        re-encrypts data with new recipients, respects original encoding
        returns True if recipients are different and secret is updated, False otherwise
        """
        fingerprints = lookup_fingerprints(recipients)
        if set(fingerprints) != set(self.fingerprints):
            data_dec = self.decrypt()
            encode_base64 = self.encoding == 'base64'
            if encode_base64:
                data_dec = base64.b64decode(data_dec).decode()
            self.encrypt(data_dec, fingerprints, encode_base64)
            return True
        return False

    def _encrypt(self, data, fingerprints, encode_base64, **kwargs_gpg):
        """
        encrypts data
        set encode_base64 to True to base64 encode data before writing
        """
        assert isinstance(fingerprints, list)
        _data = data
        self.encoding = "original"
        if encode_base64:
            _data = base64.b64encode(data.encode())
            self.encoding = "base64"
        enc = gpg_obj().encrypt(_data, fingerprints, sign=True, armor=False, **kwargs_gpg)
        if enc.ok:
            self.data = base64.b64encode(enc.data).decode()
            self.recipients = [{'fingerprint': f} for f in fingerprints]
        else:
            raise GPGError(enc.status)

    def _decrypt(self, data, **kwargs_gpg):
        """decrypt data"""
        dec = gpg_obj().decrypt(data, **kwargs_gpg)
        if dec.ok:
            return dec.data.decode()
        else:
            raise GPGError(dec.status)


class GPGBackend(RefBackend):
    def __init__(self, path, ref_type=GPGSecret):
        "init GPGBackend ref backend type"
        super().__init__(path, ref_type)
        self.type = 'gpg'
        self.gpg = gpg_obj()


def search_target_token_paths(target_secrets_path, targets):
    """
    returns dict of target and their secret token paths in target_secrets_path
    targets is a set of target names used to lookup targets in target_secrets_path
    """
    target_files = defaultdict(list)
    for root, _, files in os.walk(target_secrets_path):
        for f in files:
            full_path = os.path.join(root, f)
            full_path = full_path[len(target_secrets_path)+1:]
            target_name = full_path.split("/")[0]
            if target_name in targets:
                logger.debug('search_target_token_paths: found %s', full_path)
                target_files[target_name].append(full_path)
    return target_files


def lookup_fingerprints(recipients):
    """returns a list of fingerprints for recipients obj"""
    lookedup = []
    for recipient in recipients:
        fingerprint = recipient.get('fingerprint')
        name = recipient.get('name')
        if fingerprint is None:
            lookedup_fingerprint = fingerprint_non_expired(name)
            lookedup.append(lookedup_fingerprint)
        else:
            # If fingerprint already set, don't lookup and reuse
            lookedup.append(fingerprint)

    # Remove duplicates, sort and return fingerprints list
    return sorted(set(lookedup))


def fingerprint_non_expired(recipient_name):
    """returns first non-expired key fingerprint for recipient_name"""
    try:
        keys = gpg_obj().list_keys(keys=(recipient_name,))
        for key in keys:
            # if 'expires' key is set and time in the future, return
            if key.get('expires') and (time.time() < int(key['expires'])):
                return key['fingerprint']
            # if 'expires' key not set, return
            elif key.get('expires') is None:
                return key['fingerprint']
            else:
                logger.debug("Key for recipient: %s with fingerprint: %s is expired, skipping",
                             recipient_name, key['fingerprint'])
        raise GPGError("Could not find valid key for recipient: %s" % recipient_name)
    except IndexError as iexp:
        raise iexp
