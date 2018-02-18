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
import hashlib
import json
import logging
import os
import re
import sys
import time
import gnupg
import yaml

from kapitan.utils import PrettyDumper

logger = logging.getLogger(__name__)

SECRET_TOKEN_TAG_PATTERN = r"(\?{([\w\:\.\-\/]+)})"  # e.g. ?{gpg:my/secret/token}
SECRET_TOKEN_ATTR_PATTERN = r"(\w+):([\w\.\-\/]+)"  # e.g. gpg:my/secret/token
SECRET_TOKEN_COMPILED_ATTR_PATTERN = r"(\w+):([\w\.\-\/]+):(\w+)"  # e.g. gpg:my/secret/token:1deadbeef


class GPGError(Exception):
    "Generic GPG errors"
    pass


class TokenError(Exception):
    "Generic Token errors"
    pass


def secret_gpg_backend():
    "return gpg secret backend"
    return gnupg.GPG()


def secret_gpg_encrypt(gpg_obj, data, recipients, **kwargs):
    "encrypt data with recipients keys"
    assert isinstance(recipients, list)
    return gpg_obj.encrypt(data, recipients, sign=True, armor=False, **kwargs)


def secret_gpg_decrypt(gpg_obj, data, **kwargs):
    "decrypt data"
    return gpg_obj.decrypt(data, **kwargs)


def secret_gpg_read(gpg_obj, secrets_path, token, **kwargs):
    "decrypt and read data for token in secrets_path"
    _, token_path = secret_token_attributes(token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        with open(full_secret_path) as fp:
            secret_obj = yaml.safe_load(fp)
            data_decoded = base64.b64decode(secret_obj['data'])
            dec = secret_gpg_decrypt(gpg_obj, data_decoded, **kwargs)
            logger.debug("Read secret %s at %s", token, full_secret_path)
            if dec.ok:
                return dec.data
            else:
                raise GPGError(dec.status)
    except IOError as ex:
        if ex.errno == errno.ENOENT:
            raise ValueError("Could not read secret '%s' at %s" %
                             (token, full_secret_path))


def secret_token_from_tag(token_tag):
    "returns token from token_tag"
    match = re.match(SECRET_TOKEN_TAG_PATTERN, token_tag)
    if match:
        _, token = match.groups()
        return token
    else:
        raise ValueError('Token tag not valid: %s' % token_tag)


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


def secret_token_compiled_attributes(token):
    "validates and returns backend, path and hash from token"
    match = re.match(SECRET_TOKEN_COMPILED_ATTR_PATTERN, token)
    if match:
        backend, token_path, token_hash = match.groups()
        logger.debug("Got token attributes %s %s %s", backend, token_path, token_hash)

        if token_path.startswith("/") or token_path.endswith("/"):
            raise TokenError("Token path must not start/end with '/' %s" % token_path)
        split_path = os.path.join(*token_path.split("/"))
        if backend != 'gpg':
            raise TokenError('Secret backend is not "gpg": %s' % token)

        return backend, split_path, token_hash
    else:
        raise ValueError('Token not valid: %s' % token)


def gpg_fingerprint(gpg_obj, recipient):
    "returns first non-expired key fingerprint for recipient"
    try:
        keys = gpg_obj.list_keys(keys=(recipient,))
        for key in keys:
            # if 'expires' key is set and time in the future, return
            if key['expires'] and (time.time() < int(key['expires'])):
                return key['fingerprint']
            # if 'expires' key not set, return
            elif not key['expires']:
                return key['fingerprint']
            else:
                logger.info("Key for recipient: %s with fingerprint: %s is expired, skipping",
                            recipient, key['fingerprint'])
        raise GPGError("Could not find valid key for recipient: %s" % recipient)
    except IndexError as iexp:
        raise iexp


def secret_gpg_write(gpg_obj, secrets_path, token, data, encode_base64, recipients, **kwargs):
    """
    encrypt and write data for token in secrets_path
    set encode_base64 to True to base64 encode data before writing
    """
    _, token_path = secret_token_attributes("gpg:%s" % token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        os.makedirs(os.path.dirname(full_secret_path))
    except OSError as ex:
        # If directory exists, pass
        if ex.errno == errno.EEXIST:
            pass
    with open(full_secret_path, "w") as fp:
        encoding = "original"
        _data = data
        if encode_base64:
            _data = base64.b64encode(data)
            encoding = "base64"
        enc = secret_gpg_encrypt(gpg_obj, _data, recipients, **kwargs)
        if enc.ok:
            b64data = base64.b64encode(enc.data)
            fingerprints = [gpg_fingerprint(gpg_obj, r) for r in recipients]
            secret_obj = {"data": b64data,
                          "encoding": encoding,
                          "recipients": [{'fingerprint': f} for f in fingerprints]}
            yaml.safe_dump(secret_obj, stream=fp, default_flow_style=False)
            logger.info("Wrote secret %s for fingerprints %s at %s", token,
                        ','.join([f[:8] for f in fingerprints]), full_secret_path)
        else:
            raise GPGError(enc.status)


def secret_gpg_raw_read(secrets_path, token):
    "load (yaml) and return the content of the secret file for token"
    _, token_path = secret_token_attributes(token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        with open(full_secret_path) as fp:
            secret_obj = yaml.safe_load(fp)
            logger.debug("Read raw secret %s at %s", token, full_secret_path)
            return secret_obj
    except IOError as ex:
        if ex.errno == errno.ENOENT:
            raise ValueError("Could not read raw secret '%s' at %s" %
                             (token, full_secret_path))


def reveal_gpg_replace(gpg_obj, secrets_path, match_obj, verify=True, **kwargs):
    "returns and verifies hash for decrypted secret from token in match_obj"
    token_tag, token = match_obj.groups()
    if verify:
        _, token_path, token_hash = secret_token_compiled_attributes(token)
        secret_raw_obj = secret_gpg_raw_read(secrets_path, token)
        secret_hash = hashlib.sha256("%s%s" % (token_path, secret_raw_obj["data"])).hexdigest()
        secret_hash = secret_hash[:8]
        logger.debug("Attempting to reveal token %s with secret hash %s", token, token_hash)
        if secret_hash != token_hash:
            raise ValueError("Currently stored secret hash: %s does not match compiled secret: %s" %
                             (secret_hash, token))
    logger.debug("Revealing %s", token_tag)
    return secret_gpg_read(gpg_obj, secrets_path, token, **kwargs)


def secret_gpg_reveal_raw(gpg_obj, secrets_path, filename, verify=True, output=None, **kwargs):
    """
    read filename and reveal content (per line search and replace) with secrets to stdout
    set filename=None to read stdin
    set verify=False to skip secret hash verification
    set output to filename to write to file object, default is stdout
    returns string with revealed content when output is not stdout
    """
    _reveal_gpg_replace = partial(reveal_gpg_replace, gpg_obj, secrets_path,
                                  verify=verify, **kwargs)
    out_raw = ''
    if filename is None:
        for line in sys.stdin:
            revealed = re.sub(SECRET_TOKEN_TAG_PATTERN, _reveal_gpg_replace, line)
            if output:
                output.write(revealed)
                out_raw += revealed
            else:
                sys.stdout.write(revealed)
    else:
        with open(filename) as fp:
            for line in fp:
                revealed = re.sub(SECRET_TOKEN_TAG_PATTERN, _reveal_gpg_replace, line)
                if output:
                    output.write(revealed)
                    out_raw += revealed
                else:
                    sys.stdout.write(revealed)

    return out_raw


def secret_gpg_reveal_obj(gpg_obj, secrets_path, obj, verify=True, **kwargs):
    "recursively updates obj with revealed secrets"
    def sub_reveal_data(data):
        _reveal_gpg_replace = partial(reveal_gpg_replace, gpg_obj, secrets_path,
                                      verify=verify, **kwargs)
        return re.sub(SECRET_TOKEN_TAG_PATTERN, _reveal_gpg_replace, data)

    if isinstance(obj, dict):
        for k, v in obj.iteritems():
            obj[k] = secret_gpg_reveal_obj(gpg_obj, secrets_path, v, verify, **kwargs)
    elif isinstance(obj, list):
        obj = [secret_gpg_reveal_obj(gpg_obj, secrets_path, item, verify, **kwargs) for item in obj]
    elif isinstance(obj, basestring):  # XXX this is python 2 specific
        obj = sub_reveal_data(obj)

    return obj


def secret_gpg_reveal_dir(gpg_obj, secrets_path, dirname, verify=True, **kwargs):
    "prints grouped output for revealed file types"
    out_json = ''
    out_yaml = ''
    out_raw = ''
    # find yaml/json/raw files and group their outputs
    for f in os.listdir(dirname):
        full_path = os.path.join(dirname, f)
        if not os.path.isfile(full_path):
            pass
        if f.endswith('.json'):
            out_json += secret_gpg_reveal_file(gpg_obj, secrets_path, full_path,
                                               verify=verify, **kwargs)
        elif f.endswith('.yml'):
            out_yaml += secret_gpg_reveal_file(gpg_obj, secrets_path, full_path,
                                               verify=verify, **kwargs)
        else:
            out_raw += secret_gpg_reveal_file(gpg_obj, secrets_path, full_path,
                                              verify=verify, **kwargs)
    if out_json:
        sys.stdout.write(out_json)
    if out_yaml:
        sys.stdout.write(out_yaml)
    if out_raw:
        sys.stdout.write(out_raw)


def secret_gpg_reveal_file(gpg_obj, secrets_path, filename, verify=True, **kwargs):
    "detects type and reveals file, returns revealed output string"
    out = None
    if filename.endswith('.json'):
        logger.debug("secret_gpg_reveal_file: revealing json file: %s", filename)
        with open(filename) as fp:
            obj = json.load(fp)
            rev_obj = secret_gpg_reveal_obj(gpg_obj, secrets_path, obj,
                                            verify=verify, **kwargs)
            out = json.dumps(rev_obj, indent=4, sort_keys=True)
    elif filename.endswith('.yml'):
        logger.debug("secret_gpg_reveal_file: revealing yml file: %s", filename)
        with open(filename) as fp:
            obj = yaml.safe_load(fp)
            rev_obj = secret_gpg_reveal_obj(gpg_obj, secrets_path, obj,
                                            verify=verify, **kwargs)
            out = yaml.dump(rev_obj, Dumper=PrettyDumper,
                            default_flow_style=False, explicit_start=True)
    else:
        logger.debug("secret_gpg_reveal_file: revealing raw file: %s", filename)
        devnull = open(os.devnull, 'w')
        out = secret_gpg_reveal_raw(gpg_obj, secrets_path, filename, output=devnull,
                                    verify=verify, **kwargs)
    return out
