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

import errno
import logging
import os
import re
import gnupg

logger = logging.getLogger(__name__)

SECRET_TOKEN_PATTERN = r"(\?\([\w-\/]+\)\?)"
SECRET_PATTERN = r"[\w-\/]+"

def secret_gpg_backend():
    "return gpg secret backend"
    return gnupg.GPG()

def secret_gpg_encrypt(gpg_obj, data, recipients):
    return gpg_obj.encrypt(data, recipients)

def secret_gpg_decrypt(gpg_obj, data):
    return gpg_obj.decrypt(data)

def secret_gpg_read(gpg_obj, secrets_path, secret_id):
    pass

def secret_gpg_write(gpg_obj, secrets_path, secret_id, data, recipients):
    full_secret_path = os.path.join(secrets_path, secret_id)
    secret_filename = os.path.basename(secret_id)
    try:
        os.makedirs(os.path.dirname(full_secret_path))
    except OSError as ex:
        # If directory exists, pass
        if ex.errno == errno.EEXIST:
            pass
    with open(full_secret_path, "w") as fp:
        enc = secret_gpg_encrypt(gpg_obj, data, recipients)
        fp.write(enc.data)
        logger.debug("Wrote secret %s at %s", secret_id, secrets_path)
