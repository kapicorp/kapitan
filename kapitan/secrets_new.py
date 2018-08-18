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
import gnupg
import logger
import time

from kapitan import references
from kapitan import cached


class GPGError(Exception):
    """Generic GPG errors"""
    pass


def gpg_obj():
    if not cached.gpg_obj:
        cached.gpg_obj = gnupg.GPG()
    return cached.gpg_obj


class GPGSecret(references.Ref):
    def __init__(self, data, recipients, encode_base64=False, from_base64=False, **kwargs):
        fingerprints = self._lookup_fingerprints(recipients)
        self._encrypt(data, fingerprints, encode_base64)  # TODO review if (gpg?) kwargs are needed
        super().__init__(self.data, from_base64, **kwargs)
        self.type = 'gpg'

    def reveal(self):
        return 'DECRYPTED DATA'  # TODO

    def _encrypt(self, data, fingerprints, encode_base64, **kwargs_gpg):
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

    def _lookup_fingerprints(self, recipients):
        """returns a list of fingerprints for recipients obj"""
        lookedup = []
        for recipient in recipients:
            fingerprint = recipient.get('fingerprint')
            name = recipient.get('name')
            if fingerprint is None:
                lookedup_fingerprint = self._gpg_fingerprint_non_expired(name)
                lookedup.append(lookedup_fingerprint)
            else:
                # If fingerprint already set, don't lookup and reuse
                lookedup.append(fingerprint)

        # Remove duplicates, sort and return fingerprints list
        return sorted(set(lookedup))

    def _gpg_fingerprint_non_expired(self, recipient_name):
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


class GPGBackend(references.RefBackend):
    def __init__(self, path, ref_type=GPGSecret):
        super().__init__(path, ref_type)
        self.type = 'gpg'
        self.gpg = gpg_obj()
