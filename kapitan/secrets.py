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

"secrets module"

import base64
import errno
from functools import partial
import logging
import os
import re
import sys
import gnupg
import yaml

logger = logging.getLogger(__name__)

SECRET_TOKEN_PATTERN = r"(\?{([\w\:\-\/]+)})" # e.g. ?{gpg:my/secret/token}
SECRET_TOKEN_ATTR_PATTERN = r"(\w+):([\w\-\/]+)" # e.g. gpg:my/secret/token

class GPGError(Exception):
    "Generic GPG errors"
    pass

class TokenError(Exception):
    "Generic Token errors"
    pass

def secret_gpg_backend():
    "return gpg secret backend"
    return gnupg.GPG()

def secret_gpg_encrypt(gpg_obj, data, recipients):
    "encrypt data with recipients keys"
    assert isinstance(recipients, list)
    return gpg_obj.encrypt(data, recipients, sign=True, armor=False)

def secret_gpg_decrypt(gpg_obj, data):
    "decrypt data"
    return gpg_obj.decrypt(data)

def secret_gpg_read(gpg_obj, secrets_path, token):
    "decrypt and read data for token in secrets_path"
    b, token_path = secret_token_attributes(token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        with open(full_secret_path) as fp:
            secret_obj = yaml.safe_load(fp)
            data_decoded = base64.b64decode(secret_obj['data'])
            dec = secret_gpg_decrypt(gpg_obj, data_decoded)
            logger.debug("Read secret %s at %s", token, full_secret_path)
            if dec.ok:
                return dec.data
            else:
                raise GPGError(dec.status)
    except IOError as ex:
        if ex.errno == errno.ENOENT:
            raise ValueError("Could not read secret '%s' at %s" %
                             (token, full_secret_path))

def secret_token_attributes(token):
    "returns backend and path from token"
    match = re.match(SECRET_TOKEN_ATTR_PATTERN, token)
    if match:
        backend, token_path = match.groups()
        logger.debug("Got token attributes %s %s", backend, token_path)

        if token_path.startswith("/") or token_path.endswith("/"):
            raise TokenError("Token path must not start/end with '/' %s" % token_path)
        split_path = os.path.join(*token_path.split("/"))
        if backend != 'gpg':
            raise TokenError('Secret backend is not "gpg": %s' % token)

        return backend, split_path
    else:
        raise ValueError('Token not valid: %s' % token)

def gpg_fingerprint(gpg_obj, recipient):
    "returns (first) key fingerprint for recipient"
    try:
        return gpg_obj.list_keys(keys=(recipient,))[0]["fingerprint"]
    except IndexError as iexp:
        raise iexp

def secret_gpg_write(gpg_obj, secrets_path, token, data, recipients):
    "encrypt and write data for token in secrets_path"
    _, token_path = secret_token_attributes("gpg:%s" % token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        os.makedirs(os.path.dirname(full_secret_path))
    except OSError as ex:
        # If directory exists, pass
        if ex.errno == errno.EEXIST:
            pass
    with open(full_secret_path, "w") as fp:
        enc = secret_gpg_encrypt(gpg_obj, data, recipients)
        if enc.ok:
            b64data = base64.b64encode(enc.data)
            fingerprints = [gpg_fingerprint(gpg_obj, r) for r in recipients]
            secret_obj = {"data": b64data,
                          "recipients": [{'fingerprint': f} for f in fingerprints]}
            yaml.safe_dump(secret_obj, stream=fp, default_flow_style=False)
            logger.info("Wrote secret %s for fingerprints %s at %s", token,
                        ','.join([f[:8] for f in fingerprints]), full_secret_path)
        else:
            raise GPGError(enc.status)

def reveal_gpg_replace(gpg_obj, secrets_path, match_obj):
    "returns decrypted secret from token in match_obj"
    token_tag, token = match_obj.groups()
    logger.debug("Revealing %s", token_tag)
    return secret_gpg_read(gpg_obj, secrets_path, token)

def secret_gpg_reveal(gpg_obj, secrets_path, filename):
    """
    read filename and reveal content with secrets to stdout
    set filename=None to read stdin
    """
    _reveal_gpg_replace = partial(reveal_gpg_replace, gpg_obj, secrets_path)
    if filename is None:
        for line in sys.stdin:
            sys.stdout.write(re.sub(SECRET_TOKEN_PATTERN, _reveal_gpg_replace, line))
    else:
        with open(filename) as fp:
            for line in fp:
                sys.stdout.write(re.sub(SECRET_TOKEN_PATTERN, _reveal_gpg_replace, line))
