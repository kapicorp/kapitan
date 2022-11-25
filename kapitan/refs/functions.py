# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"reference functions"

import base64
import hashlib
import logging
import secrets  # python secrets module
import string

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from kapitan.errors import RefError

logger = logging.getLogger(__name__)


def eval_func(func_name, ctx, *func_params):
    """calls specific function which generates the secret"""
    func_lookup = get_func_lookup()

    return func_lookup[func_name](ctx, *func_params)


def get_func_lookup():
    """returns the lookup-table for the generator functions"""
    return {
        "randomstr": randomstr,
        "random": random,
        "sha256": sha256,
        "ed25519": ed25519_private_key,
        "rsa": rsa_private_key,
        "rsapublic": rsa_public_key,
        "publickey": public_key,
        "reveal": reveal,
        "loweralphanum": loweralphanum,
        "basicauth": basicauth,
    }


def randomstr(ctx, nbytes=""):
    """
    generates a URL-safe text string, containing nbytes random bytes
    sets it to ctx.data
    """
    # deprecated function
    logger.info("DeprecationWarning: randomstr is deprecated. Use random:str instead")
    random(ctx, "str", nbytes)


def sha256(ctx, salt=""):
    """sets ctx.data to salted sha256 hexdigest for input_value"""
    if ctx.data:
        salted_input_value = salt + ":" + ctx.data
        ctx.data = hashlib.sha256(salted_input_value.encode()).hexdigest()
    else:
        raise RefError(
            "Ref error: eval_func: nothing to sha256 hash; try " "something like '|random:str|sha256'"
        )


def ed25519_private_key(ctx):
    """sets ctx.data to a ed25519 private key"""

    key = ed25519.Ed25519PrivateKey.generate()

    ctx.data = str(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        "utf-8",
    )


def rsa_private_key(ctx, key_size="4096"):
    """sets ctx.data to a RSA private key of key_size, default 4096"""
    rsa_key_size = int(key_size)

    key = rsa.generate_private_key(public_exponent=65537, key_size=rsa_key_size, backend=default_backend())

    ctx.data = str(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        "utf-8",
    )


def rsa_public_key(ctx):
    """Derives RSA public key from revealed private key"""
    if not ctx.data:
        raise RefError(
            "Ref error: eval_func: RSA public key cannot be derived; try "
            "something like '|reveal:path/to/encrypted_private_key|rsapublic'"
        )

    public_key(ctx)


def public_key(ctx):
    """Derives RSA public key from revealed private key"""
    if not ctx.data:
        raise RefError(
            "Ref error: eval_func: public key cannot be derived; try "
            "something like '|reveal:path/to/encrypted_private_key|publickey'"
        )

    data_dec = ctx.data
    if ctx.ref_encoding == "base64":
        data_dec = base64.b64decode(data_dec).decode()

    private_key = serialization.load_pem_private_key(
        data_dec.encode(), password=None, backend=default_backend()
    )
    public_key = private_key.public_key()

    ctx.data = str(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
        "UTF-8",
    )


def reveal(ctx, secret_path):
    """
    decrypt and return data from secret_path
    """
    token_type_name = ctx.ref_controller.token_type_name(ctx.token)
    secret_tag = "?{{{}:{}}}".format(token_type_name, secret_path)
    try:
        ref_obj = ctx.ref_controller[secret_tag]
        ctx.ref_encoding = ref_obj.encoding
        ctx.data = ref_obj.reveal()
    except KeyError:
        raise RefError(
            f"|reveal function error: {secret_path} file in {ctx.token}|reveal:{secret_path} does not exist"
        )


def loweralphanum(ctx, nchars="8"):
    """generates a DNS-compliant text string (a-z and 0-9), containing lower alphanum chars"""
    # deprecated function
    logger.info("DeprecationWarning: loweralphanum is deprecated. Use random:loweralphanum instead")
    random(ctx, "loweralphanum", nchars)


def random(ctx, type="str", nchars="", special_chars=string.punctuation):
    """
    generates a text string, containing nchars of given type
    """

    pool_lookup = {
        "str": string.ascii_letters + string.digits + "-_",
        "int": string.digits,
        "loweralpha": string.ascii_lowercase,
        "upperalpha": string.ascii_uppercase,
        "loweralphanum": string.ascii_lowercase + string.digits,
        "upperalphanum": string.ascii_uppercase + string.digits,
        "special": string.ascii_letters + string.digits + special_chars,
    }

    default_nchars_lookup = {
        "str": 43,
        "int": 16,
    }

    # get pool of given type
    pool = pool_lookup.get(type, None)
    if not pool:
        raise RefError(
            "{}: unknown random type used. Choose one of {}".format(type, [key for key in pool_lookup])
        )

    # get default value for nchars if nchars is not specified
    if not nchars:
        nchars = default_nchars_lookup.get(type, 8)
    else:
        # check input for nchars
        try:
            nchars = int(nchars)
        except ValueError:
            raise RefError(f"Ref error: eval_func: {nchars} cannot be converted into integer.")

    # check if any special characters are specified without using type special
    if type != "special" and special_chars != string.punctuation:
        raise RefError(
            "Ref error: eval_func: {} has no option to use special characters. Use type special instead, i.e. ||random:special:{}".format(
                type, special_chars
            )
        )

    # check if pool is valid, eliminates duplicates
    allowed_pool = string.ascii_letters + string.digits + string.punctuation
    pool = "".join(set(pool).intersection(allowed_pool))

    # generate string based on given pool
    generated_str = "".join(secrets.choice(pool) for i in range(nchars))

    # set ctx.data to generated string
    ctx.data = generated_str


def basicauth(ctx, username="", password=""):
    # check if parameters are specified
    if not username:
        # use random pet name as username
        username = "".join(secrets.choice(string.ascii_lowercase) for i in range(8))

    if not password:
        # generate random password
        pool = string.ascii_letters + string.digits
        password = "".join(secrets.choice(pool) for i in range(8))
    # generate basic-auth token (base64-encoded)
    token = username + ":" + password
    token_bytes = token.encode()
    token_bytes_b64 = base64.b64encode(token_bytes)
    token_b64 = token_bytes_b64.decode()

    # set generated token to ctx.data
    ctx.data = token_b64
