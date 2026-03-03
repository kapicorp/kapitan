#!/usr/bin/env python3

import base64
import hashlib
import string

import pytest

from kapitan.errors import RefError
from kapitan.refs import functions


class _Ctx:
    def __init__(
        self,
        data=None,
        ref_encoding="original",
        ref_controller=None,
        token="base64:path",
    ):
        self.data = data
        self.ref_encoding = ref_encoding
        self.ref_controller = ref_controller
        self.token = token


def test_get_func_lookup_contains_expected_functions():
    lookup = functions.get_func_lookup()
    assert {
        "randomstr",
        "random",
        "sha256",
        "ed25519",
        "rsa",
        "rsapublic",
        "publickey",
        "reveal",
        "loweralphanum",
        "basicauth",
    }.issubset(lookup.keys())


def test_eval_func_dispatches_sha256():
    ctx = _Ctx(data="secret")
    functions.eval_func("sha256", ctx, "salt")

    expected = hashlib.sha256(b"salt:secret").hexdigest()
    assert ctx.data == expected


def test_sha256_raises_on_empty_data():
    with pytest.raises(RefError):
        functions.sha256(_Ctx(data=None))


def test_random_unknown_type_raises():
    with pytest.raises(RefError, match="unknown random type"):
        functions.random(_Ctx(), "unknown")


def test_random_invalid_nchars_raises():
    with pytest.raises(RefError, match="cannot be converted into integer"):
        functions.random(_Ctx(), "str", "NaN")


def test_random_special_chars_not_allowed_for_non_special_type():
    with pytest.raises(RefError, match="has no option to use special characters"):
        functions.random(_Ctx(), "str", "8", special_chars="@")


def test_random_loweralphanum_output_shape():
    ctx = _Ctx()
    functions.random(ctx, "loweralphanum", "16")
    assert len(ctx.data) == 16
    assert set(ctx.data).issubset(set(string.ascii_lowercase + string.digits))


def test_basicauth_encodes_supplied_credentials():
    ctx = _Ctx()
    functions.basicauth(ctx, "user", "pass")
    assert base64.b64decode(ctx.data.encode()).decode() == "user:pass"


def test_public_key_raises_on_missing_input():
    with pytest.raises(RefError, match="public key cannot be derived"):
        functions.public_key(_Ctx(data=""))


def test_rsa_public_key_raises_on_missing_input():
    with pytest.raises(RefError, match="RSA public key cannot be derived"):
        functions.rsa_public_key(_Ctx(data=""))


def test_public_key_decodes_base64_private_key():
    private_ctx = _Ctx()
    functions.rsa_private_key(private_ctx, "1024")

    encoded_private_key = base64.b64encode(private_ctx.data.encode()).decode()
    public_ctx = _Ctx(data=encoded_private_key, ref_encoding="base64")
    functions.public_key(public_ctx)

    assert "BEGIN PUBLIC KEY" in public_ctx.data


def test_reveal_sets_context_on_success():
    class _Ref:
        encoding = "base64"

        @staticmethod
        def reveal():
            return "revealed-value"

    class _RefController:
        @staticmethod
        def token_type_name(_token):
            return "base64"

        @staticmethod
        def __getitem__(_tag):
            return _Ref()

    ctx = _Ctx(ref_controller=_RefController(), token="base64:any/path")
    functions.reveal(ctx, "secret/path")

    assert ctx.ref_encoding == "base64"
    assert ctx.data == "revealed-value"


def test_reveal_raises_when_secret_is_missing():
    class _MissingRefController:
        @staticmethod
        def token_type_name(_token):
            return "base64"

        @staticmethod
        def __getitem__(_tag):
            raise KeyError("missing")

    ctx = _Ctx(ref_controller=_MissingRefController(), token="base64:any/path")
    with pytest.raises(RefError, match="does not exist"):
        functions.reveal(ctx, "missing/path")


def test_loweralphanum_wrapper_generates_expected_charset():
    ctx = _Ctx()
    functions.loweralphanum(ctx, "10")

    assert len(ctx.data) == 10
    assert set(ctx.data).issubset(set(string.ascii_lowercase + string.digits))


def test_basicauth_generates_defaults_when_values_missing(monkeypatch):
    generated = iter(list("abcdefgh") + list("A1B2C3D4"))
    monkeypatch.setattr(
        "kapitan.refs.functions.secrets.choice", lambda _pool: next(generated)
    )

    ctx = _Ctx()
    functions.basicauth(ctx)

    decoded = base64.b64decode(ctx.data.encode()).decode()
    assert decoded == "abcdefgh:A1B2C3D4"
