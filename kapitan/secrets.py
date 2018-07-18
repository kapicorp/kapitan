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

"secrets module"


import base64
from collections import defaultdict
import errno
from functools import partial
import hashlib
import ujson as json
import logging
import os
import re
import secrets
import sys
import time
import gnupg
import yaml
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from six import string_types
from kapitan.utils import PrettyDumper
from kapitan.errors import SecretError
import kapitan.cached as cached

logger = logging.getLogger(__name__)

# e.g. ?{gpg:my/secret/token} or ?{gpg:my/secret/token|func:param1:param2}
SECRET_TOKEN_TAG_PATTERN = r"(\?{([\w\:\.\-\/]+)([\|\w\:\.\-\/]+)*})"
SECRET_TOKEN_ATTR_PATTERN = r"(\w+):([\w\.\-\/]+)"  # e.g. gpg:my/secret/token
SECRET_TOKEN_COMPILED_ATTR_PATTERN = r"(\w+):([\w\.\-\/]+):(\w+)"  # e.g. gpg:my/secret/token:1deadbeef

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader


class GPGError(Exception):
    """Generic GPG errors"""
    pass


class TokenError(Exception):
    """Generic Token errors"""
    pass


def secret_gpg_backend():
    """return gpg secret backend"""
    if not cached.gpg_backend:
        cached.gpg_backend = gnupg.GPG()

    return cached.gpg_backend


def secret_gpg_encrypt(data, fingerprints, **kwargs):
    """encrypt data with fingerprints keys"""
    assert isinstance(fingerprints, list)
    return secret_gpg_backend().encrypt(data, fingerprints, sign=True, armor=False, **kwargs)


def secret_gpg_decrypt(data, **kwargs):
    """decrypt data"""
    return secret_gpg_backend().decrypt(data, **kwargs)


def secret_gpg_read(secrets_path, token, **kwargs):
    """decrypt and read data for token in secrets_path"""
    _, token_path = secret_token_attributes(token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        with open(full_secret_path) as fp:
            secret_obj = yaml.load(fp, Loader=YamlLoader)
            data_decoded = base64.b64decode(secret_obj['data'])
            dec = secret_gpg_decrypt(data_decoded, **kwargs)
            logger.debug("Read secret %s at %s", token, full_secret_path)
            if dec.ok:
                return dec.data.decode("UTF-8")
            else:
                raise GPGError(dec.status)
    except IOError as ex:
        if ex.errno == errno.ENOENT:
            logger.error('Secret error: Could not read secret %s at %s',
                         token, full_secret_path)
            raise SecretError()


def secret_token_from_tag(token_tag):
    """returns token from token_tag"""
    match = re.match(SECRET_TOKEN_TAG_PATTERN, token_tag)
    if match:
        _, token, func = match.groups()
        return token, func
    else:
        logger.error('Secret error: token tag not valid: %s', token_tag)
        raise SecretError()


def secret_token_attributes(token):
    """returns backend and path from token"""
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
        logger.error('Secret error: token not valid: %s', token)
        raise SecretError()


def secret_token_compiled_attributes(token):
    """validates and returns backend, path and hash from token"""
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
        logger.error('Secret error: token not valid: %s', token)
        raise SecretError()


def gpg_fingerprint_non_expired(recipient_name):
    """returns first non-expired key fingerprint for recipient_name"""
    try:
        keys = secret_gpg_backend().list_keys(keys=(recipient_name,))
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


def secret_gpg_write(secrets_path, token, data, encode_base64, recipients, **kwargs):
    """
    encrypt and write data for token in secrets_path
    set encode_base64 to True to base64 encode data before writing
    recipients is a list of dictionaries with keys: name(required) fingerprint(optional)
    if fingerprint key is not set in recipients, the first non-expired fingerprint will be used
    if fingerprint is set, there will be no name based lookup
    """
    _, token_path = secret_token_attributes("gpg:%s" % token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        os.makedirs(os.path.dirname(full_secret_path))
    except OSError as ex:
        # If directory exists, pass
        if ex.errno == errno.EEXIST:
            pass

    encoding = "original"
    _data = data
    if encode_base64:
        _data = base64.b64encode(data.encode("UTF-8"))
        encoding = "base64"
    fingerprints = lookup_fingerprints(recipients)
    enc = secret_gpg_encrypt(_data, fingerprints, **kwargs)
    if enc.ok:
        b64data = base64.b64encode(enc.data).decode("UTF-8")
        secret_obj = {"data": b64data,
                      "encoding": encoding,
                      "recipients": [{'fingerprint': f} for f in fingerprints]}
        with open(full_secret_path, "w") as fp:
            yaml.safe_dump(secret_obj, stream=fp, default_flow_style=False)
            logger.info("Wrote secret %s for fingerprints %s at %s", token,
                        ','.join([f[:8] for f in fingerprints]), full_secret_path)
    else:
        raise GPGError(enc.status)


def secret_gpg_raw_read(secrets_path, token):
    """load (yaml) and return the content of the secret file for token"""
    _, token_path = secret_token_attributes(token)
    full_secret_path = os.path.join(secrets_path, token_path)
    try:
        with open(full_secret_path) as fp:
            secret_obj = yaml.load(fp, Loader=YamlLoader)
            logger.debug("Read raw secret %s at %s", token, full_secret_path)
            return secret_obj
    except IOError as ex:
        if ex.errno == errno.ENOENT:
            logger.error('Secret error: could not read raw secret %s at %s',
                         token, full_secret_path)
            raise SecretError()


def reveal_gpg_replace(secrets_path, match_obj, verify=True, **kwargs):
    """returns and verifies hash for decrypted secret from token in match_obj"""
    token_tag, token, func = match_obj.groups()
    if verify:
        _, token_path, token_hash = secret_token_compiled_attributes(token)
        secret_raw_obj = secret_gpg_raw_read(secrets_path, token)
        secret_tag = "%s%s" % (token_path, secret_raw_obj["data"])
        secret_hash = hashlib.sha256(secret_tag.encode("UTF-8")).hexdigest()
        secret_hash = secret_hash[:8]
        logger.debug("Attempting to reveal token %s with secret hash %s", token, token_hash)
        if secret_hash != token_hash:
            logger.error("Secret error: currently stored secret hash: %s does not match compiled secret: %s",
                         secret_hash, token)
            raise SecretError()

    logger.debug("Revealing %s", token_tag)
    return secret_gpg_read(secrets_path, token, **kwargs)


def secret_gpg_update_recipients(secrets_path, token_path, recipients, **kwargs):
    """updates the recipient list for secret in token_path"""
    token = "gpg:%s" % token_path
    secret_raw_obj = secret_gpg_raw_read(secrets_path, token)
    data_dec = secret_gpg_read(secrets_path, token, **kwargs)
    encode_base64 = secret_raw_obj.get('encoding', None) == 'base64'

    if encode_base64:
        data_dec = base64.b64decode(data_dec).decode('UTF-8')

    secret_gpg_write(secrets_path, token_path, data_dec, encode_base64,
                     recipients, **kwargs)


def secret_gpg_reveal_raw(secrets_path, filename, verify=True, output=None, **kwargs):
    """
    read filename and reveal content (per line search and replace) with secrets to stdout
    set filename=None to read stdin
    set verify=False to skip secret hash verification
    set output to filename to write to file object, default is stdout
    returns string with revealed content when output is not stdout
    """
    _reveal_gpg_replace = partial(reveal_gpg_replace, secrets_path,
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


def secret_gpg_reveal_obj(secrets_path, obj, verify=True, **kwargs):
    """recursively updates obj with revealed secrets"""
    def sub_reveal_data(data):
        _reveal_gpg_replace = partial(reveal_gpg_replace, secrets_path,
                                      verify=verify, **kwargs)
        return re.sub(SECRET_TOKEN_TAG_PATTERN, _reveal_gpg_replace, data)

    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = secret_gpg_reveal_obj(secrets_path, v, verify, **kwargs)
    elif isinstance(obj, list):
        obj = [secret_gpg_reveal_obj(secrets_path, item, verify, **kwargs) for item in obj]
    elif isinstance(obj, string_types):
        obj = sub_reveal_data(obj)

    return obj


def secret_gpg_reveal_dir(secrets_path, dirname, verify=True, **kwargs):
    """prints grouped output for revealed file types"""
    out_json = ''
    out_yaml = ''
    out_raw = ''
    # find yaml/json/raw files and group their outputs
    for f in os.listdir(dirname):
        full_path = os.path.join(dirname, f)
        if not os.path.isfile(full_path):
            pass
        if f.endswith('.json'):
            out_json += secret_gpg_reveal_file(secrets_path, full_path,
                                               verify=verify, **kwargs)
        elif f.endswith('.yml'):
            out_yaml += secret_gpg_reveal_file(secrets_path, full_path,
                                               verify=verify, **kwargs)
        else:
            out_raw += secret_gpg_reveal_file(secrets_path, full_path,
                                              verify=verify, **kwargs)
    if out_json:
        sys.stdout.write(out_json)
    if out_yaml:
        sys.stdout.write(out_yaml)
    if out_raw:
        sys.stdout.write(out_raw)


def secret_gpg_reveal_file(secrets_path, filename, verify=True, **kwargs):
    """detects type and reveals file, returns revealed output string"""
    out = None
    if filename.endswith('.json'):
        logger.debug("secret_gpg_reveal_file: revealing json file: %s", filename)
        with open(filename) as fp:
            obj = json.load(fp)
            rev_obj = secret_gpg_reveal_obj(secrets_path, obj,
                                            verify=verify, **kwargs)
            out = json.dumps(rev_obj, indent=4, sort_keys=True)
    elif filename.endswith('.yml'):
        logger.debug("secret_gpg_reveal_file: revealing yml file: %s", filename)
        with open(filename) as fp:
            obj = yaml.load(fp, Loader=YamlLoader)
            rev_obj = secret_gpg_reveal_obj(secrets_path, obj,
                                            verify=verify, **kwargs)
            out = yaml.dump(rev_obj, Dumper=PrettyDumper,
                            default_flow_style=False, explicit_start=True)
    else:
        logger.debug("secret_gpg_reveal_file: revealing raw file: %s", filename)
        with open(os.devnull, 'w') as devnull:
            out = secret_gpg_reveal_raw(secrets_path, filename, output=devnull,
                                        verify=verify, **kwargs)
    return out


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
            lookedup_fingerprint = gpg_fingerprint_non_expired(name)
            lookedup.append(lookedup_fingerprint)
        else:
            # If fingerprint already set, don't lookup and reuse
            lookedup.append(fingerprint)

    # Remove duplicates, sort and return fingerprints list
    return sorted(set(lookedup))


def secret_gpg_raw_read_fingerprints(secrets_path, token_path):
    """returns fingerprint list in raw secret for token_path"""
    token = "gpg:%s" % token_path
    secret_raw_obj = secret_gpg_raw_read(secrets_path, token)
    secret_raw_obj_fingerprints = [r['fingerprint'] for r in secret_raw_obj['recipients']]
    return secret_raw_obj_fingerprints


def secret_gpg_exists(secrets_path, token_path):
    """checks if a secret with token exists in secrets_path"""
    full_secret_path = os.path.join(secrets_path, token_path)

    return os.path.exists(full_secret_path)


def randomstr(nbytes=''):
    """generates a URL-safe text string, containing nbytes random bytes"""
    if nbytes:
        nbytes = int(nbytes)
        return secrets.token_urlsafe(nbytes)
    return secrets.token_urlsafe()


def rsa_private_key(key_size=''):
    """generates an RSA private key of key_size, default 4096"""
    rsa_key_size = 4096
    if key_size:
        rsa_key_size = int(key_size)

    key = rsa.generate_private_key(public_exponent=65537, key_size=rsa_key_size, backend=default_backend())

    return str(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ), "UTF-8")


def rsa_public_key(secrets_path, private_key_file, passphrase=None):
    """derives an RSA public key from private_key_file"""
    token = "gpg:{}".format(private_key_file)
    secret_raw_obj = secret_gpg_raw_read(secrets_path, token)
    data_dec = secret_gpg_read(secrets_path, token, passphrase=passphrase)
    encoded_base64 = secret_raw_obj.get('encoding', None) == 'base64'

    if encoded_base64:
        data_dec = base64.b64decode(data_dec).decode('UTF-8')

    private_key = serialization.load_pem_private_key(data_dec.encode(), password=None, backend=default_backend())
    public_key = private_key.public_key()

    return str(public_key.public_bytes(
       encoding=serialization.Encoding.PEM,
       format=serialization.PublicFormat.SubjectPublicKeyInfo
    ), "UTF-8")


def secret_gpg_write_function(secrets_path, token, func, recipients, **kwargs):
    """
    encrypt and write data returned by func for token in secrets_path
    essentially runs secret_gpg_write() where data is the evaluation of func
    """

    # support for pipes. e.g |randomstr|base64
    functions = func.split('|')
    # Remove first element as it's not a function, just emtpy space
    del functions[0]

    data = None
    encode_base64 = False

    for function in functions:
        # func params are split by ':'. e.g. randomstr:12
        func_name, *func_params = function.strip().split(':')

        if func_name == 'randomstr':
            data = randomstr(*func_params)

        elif func_name == 'rsa':
            data = rsa_private_key(*func_params)

        elif func_name == 'rsapublic':
            if len(func_params) == 0:
                logger.error("Secret error: secret_gpg_write_function: private key file not specified; try " +
                    "something like 'rsapublic:path/to/encrypted_private_key'", func)
                raise SecretError
            else:
                data = rsa_public_key(secrets_path, passphrase=kwargs.get('passphrase', None), *func_params)

        elif func_name == 'base64':
            if data:
                encode_base64 = True
            else:
                logger.error("Secret error: secret_gpg_write_function: nothing to base64 encode; try " +
                    "something like 'randomstr|base64'", func)
                raise SecretError

        elif func_name == 'sha256':
            if data:
                salt = ''
                if len(func_params) > 0:
                    salt = func_params[0]
                    salt += ":"

                salted_data = salt + data
                data = hashlib.sha256(salted_data.encode("UTF-8")).hexdigest()
            else:
                logger.error("Secret error: secret_gpg_write_function: nothing to sha256 hash; try " +
                    "something like 'randomstr|sha256'", func)
                raise SecretError

        else:
            logger.error("Secret error: secret_gpg_write_function: unknown func: %s", func)
            raise SecretError

    secret_gpg_write(secrets_path, token, data, encode_base64, recipients, **kwargs)
