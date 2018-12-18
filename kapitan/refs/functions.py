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

"reference functions"

import base64
import hashlib
import logging
import secrets  # python secrets module

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kapitan.errors import RefError

logger = logging.getLogger(__name__)


def eval_func(func_name, ctx, *func_params):

    func_lookup = {
        'randomstr': randomstr,
        'sha256': sha256,
        'rsa': rsa_private_key,
        'rsapublic': rsa_public_key
    }

    return func_lookup[func_name](ctx, *func_params)


def randomstr(ctx, nbytes=''):
    """
    generates a URL-safe text string, containing nbytes random bytes
    sets it to ctx.data
    """
    if nbytes:
        nbytes = int(nbytes)
        ctx.data = secrets.token_urlsafe(nbytes)
    else:
        ctx.data = secrets.token_urlsafe()


def sha256(ctx, salt=''):
    """sets ctx.data to salted sha256 hexdigest for input_value"""
    if ctx.data:
        salted_input_value = salt + ":" + ctx.data
        ctx.data = hashlib.sha256(salted_input_value.encode()).hexdigest()
    else:
        raise RefError("Ref error: eval_func: nothing to sha256 hash; try "
                       "something like 'randomstr|sha256'")


def rsa_private_key(ctx, key_size='4096'):
    """sets ctx.data to a RSA private key of key_size, default 4096"""
    rsa_key_size = int(key_size)

    key = rsa.generate_private_key(public_exponent=65537, key_size=rsa_key_size,
                                   backend=default_backend())

    ctx.data = str(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ), "utf-8")


def rsa_public_key(ctx, private_key_token_path):
    """sets ctx.data to derived RSA public key from private_key_token_path"""
    # load and decrypt secret content in private_key_token_path
    token_type_name = ctx.ref_controller.token_type_name(ctx.token)
    private_key_tag = "?{{{}:{}}}".format(token_type_name, private_key_token_path)
    ref_obj = ctx.ref_controller[private_key_tag]
    data_dec = ref_obj.reveal()

    if ref_obj.encoding == 'base64':
        data_dec = base64.b64decode(data_dec).decode()

    private_key = serialization.load_pem_private_key(data_dec.encode(), password=None, backend=default_backend())
    public_key = private_key.public_key()

    ctx.data = str(public_key.public_bytes(
                   encoding=serialization.Encoding.PEM,
                   format=serialization.PublicFormat.SubjectPublicKeyInfo
                   ), "UTF-8")
