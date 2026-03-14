#!/usr/bin/env python3

import base64
import logging
from types import SimpleNamespace

import pytest

from kapitan import cached
from kapitan.refs.base import RefError
from kapitan.refs.secrets.gkms import GoogleKMSError, GoogleKMSSecret, gkms_obj


class _FailingClient:
    def encrypt(self, *args, **kwargs):
        raise RuntimeError("boom")

    def decrypt(self, *args, **kwargs):
        raise RuntimeError("boom")


class _GkmsRequest:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _FakeGkmsClient:
    def encrypt(self, name, body):
        ciphertext = base64.b64encode(base64.b64encode(b"cipher")).decode("ascii")
        return _GkmsRequest({"ciphertext": ciphertext})

    def decrypt(self, name, body):
        plaintext = base64.b64encode(b"plain").decode("ascii")
        return _GkmsRequest({"plaintext": plaintext})


@pytest.fixture(autouse=True)
def reset_cached_after():
    yield
    cached.reset_cache()


def test_gkms_encrypt_error(monkeypatch):
    monkeypatch.setattr("kapitan.refs.secrets.gkms.gkms_obj", lambda: _FailingClient())
    with pytest.raises(GoogleKMSError):
        GoogleKMSSecret("data", "real", encrypt=True)


def test_gkms_decrypt_error(monkeypatch):
    monkeypatch.setattr("kapitan.refs.secrets.gkms.gkms_obj", lambda: _FailingClient())
    secret = GoogleKMSSecret(b"data", "real", encrypt=False)
    secret.key = "real"
    with pytest.raises(GoogleKMSError):
        secret._decrypt(base64.b64encode(b"cipher"))


def test_gkms_encrypt_decrypt_and_update(monkeypatch):
    monkeypatch.setattr("kapitan.refs.secrets.gkms.gkms_obj", lambda: _FakeGkmsClient())
    secret = GoogleKMSSecret("data", "key", encrypt=True)
    assert secret.reveal() == "plain"
    assert secret.update_key("new-key") is True
    assert secret.key == "new-key"


def test_gkms_update_key_no_change():
    gkms = GoogleKMSSecret(b"data", "mock", encrypt=False)
    assert gkms.update_key("mock") is False


def test_gkms_from_params():
    secrets = SimpleNamespace(gkms=SimpleNamespace(key="mock"))
    cached.inv = SimpleNamespace(
        get_parameters=lambda _target: SimpleNamespace(
            kapitan=SimpleNamespace(secrets=secrets)
        )
    )

    try:
        assert (
            GoogleKMSSecret.from_params(
                "data", SimpleNamespace(kwargs={"target_name": "t"})
            ).key
            == "mock"
        )
    finally:
        cached.inv = None


def test_gkms_obj_caches_client_and_configures_logging(monkeypatch):
    calls = {"build": 0}
    fake_client = object()

    class _BuildChain:
        @staticmethod
        def projects():
            return _BuildChain()

        @staticmethod
        def locations():
            return _BuildChain()

        @staticmethod
        def keyRings():
            return _BuildChain()

        @staticmethod
        def cryptoKeys():
            return fake_client

    def _build(*_args, **_kwargs):
        calls["build"] += 1
        return _BuildChain()

    monkeypatch.setattr("kapitan.refs.secrets.gkms.gcloud.build", _build)
    monkeypatch.setattr(
        "kapitan.refs.secrets.gkms.logger.getEffectiveLevel", lambda: 20
    )
    cached.gkms_obj = None

    assert gkms_obj() is fake_client
    assert gkms_obj() is fake_client
    assert calls["build"] == 1


def test_gkms_from_params_error_paths():
    with pytest.raises(ValueError, match="target_name not set"):
        GoogleKMSSecret.from_params(
            "data", SimpleNamespace(kwargs={"target_name": None})
        )

    with pytest.raises(RefError, match="target_name missing"):
        GoogleKMSSecret.from_params("data", SimpleNamespace(kwargs={}))


def test_gkms_base64_update_and_encrypt_bytes(monkeypatch):
    encoded = GoogleKMSSecret("data", "mock", encrypt=True, encode_base64=True)
    assert encoded.encoding == "base64"

    secret = GoogleKMSSecret(b"ciphertext", "mock", encrypt=False)
    secret.encoding = "base64"

    monkeypatch.setattr(
        GoogleKMSSecret,
        "reveal",
        lambda self: base64.b64encode(b"decoded").decode(),
    )
    captured = {}
    original_encrypt = GoogleKMSSecret._encrypt

    def _capture_encrypt(self, data, key, encode_base64):
        captured["data"] = data
        captured["key"] = key
        captured["encode_base64"] = encode_base64
        self.data = b"reencrypted"
        self.key = key

    monkeypatch.setattr(GoogleKMSSecret, "_encrypt", _capture_encrypt)

    assert secret.update_key("new-key") is True
    assert captured == {"data": "decoded", "key": "new-key", "encode_base64": True}
    assert secret.data == "cmVlbmNyeXB0ZWQ="
    original_encrypt(secret, b"bytes", "mock", encode_base64=False)
    assert secret.key == "mock"


def test_gkms_obj_keeps_google_logger_unchanged_in_debug_mode(monkeypatch):
    calls = {"set_level_calls": 0, "build_calls": 0}
    fake_client = object()

    class _BuildChain:
        @staticmethod
        def projects():
            return _BuildChain()

        @staticmethod
        def locations():
            return _BuildChain()

        @staticmethod
        def keyRings():
            return _BuildChain()

        @staticmethod
        def cryptoKeys():
            return fake_client

    class _FakeGoogleLogger:
        @staticmethod
        def setLevel(_level):
            calls["set_level_calls"] += 1

    real_get_logger = logging.getLogger

    def _get_logger(name=None):
        if name == "googleapiclient.discovery":
            return _FakeGoogleLogger()
        return real_get_logger(name)

    def _build(*_args, **_kwargs):
        calls["build_calls"] += 1
        return _BuildChain()

    monkeypatch.setattr(
        "kapitan.refs.secrets.gkms.logger.getEffectiveLevel", lambda: logging.DEBUG
    )
    monkeypatch.setattr("kapitan.refs.secrets.gkms.logging.getLogger", _get_logger)
    monkeypatch.setattr("kapitan.refs.secrets.gkms.gcloud.build", _build)

    cached.gkms_obj = None
    assert gkms_obj() is fake_client
    assert calls["build_calls"] == 1
    assert calls["set_level_calls"] == 0
