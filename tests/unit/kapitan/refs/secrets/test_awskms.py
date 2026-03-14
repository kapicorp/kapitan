#!/usr/bin/env python3

import base64
from types import SimpleNamespace

import pytest

from kapitan import cached
from kapitan.refs.base import RefError
from kapitan.refs.secrets.awskms import AWSKMSError, AWSKMSSecret, awskms_obj


class _FailingClient:
    def encrypt(self, *args, **kwargs):
        raise RuntimeError("boom")

    def decrypt(self, *args, **kwargs):
        raise RuntimeError("boom")


class _FakeAwsClient:
    def encrypt(self, KeyId, Plaintext):
        return {"CiphertextBlob": b"ciphertext"}

    def decrypt(self, CiphertextBlob):
        return {"Plaintext": b"plaintext"}


@pytest.fixture(autouse=True)
def reset_cached_after():
    yield
    cached.reset_cache()


def test_awskms_encrypt_error(monkeypatch):
    monkeypatch.setattr(
        "kapitan.refs.secrets.awskms.awskms_obj", lambda: _FailingClient()
    )
    with pytest.raises(AWSKMSError):
        AWSKMSSecret("data", "real", encrypt=True)


def test_awskms_decrypt_error(monkeypatch):
    monkeypatch.setattr(
        "kapitan.refs.secrets.awskms.awskms_obj", lambda: _FailingClient()
    )
    secret = AWSKMSSecret(b"data", "real", encrypt=False)
    secret.key = "real"
    with pytest.raises(AWSKMSError):
        secret._decrypt(base64.b64encode(b"cipher"))


def test_awskms_encrypt_decrypt_and_update(monkeypatch):
    monkeypatch.setattr(
        "kapitan.refs.secrets.awskms.awskms_obj", lambda: _FakeAwsClient()
    )
    secret = AWSKMSSecret("data", "key", encrypt=True)
    assert secret.reveal() == "plaintext"
    assert secret.update_key("new-key") is True
    assert secret.key == "new-key"


def test_awskms_update_key_no_change():
    awskms = AWSKMSSecret(b"data", "mock", encrypt=False)
    assert awskms.update_key("mock") is False


def test_awskms_from_params():
    secrets = SimpleNamespace(awskms=SimpleNamespace(key="mock"))
    cached.inv = SimpleNamespace(
        get_parameters=lambda _target: SimpleNamespace(
            kapitan=SimpleNamespace(secrets=secrets)
        )
    )

    try:
        assert (
            AWSKMSSecret.from_params(
                "data", SimpleNamespace(kwargs={"target_name": "t"})
            ).key
            == "mock"
        )
    finally:
        cached.inv = None


def test_awskms_obj_caches_boto_client(monkeypatch):
    calls = {"session": 0}

    class _FakeSession:
        @staticmethod
        def client(name):
            assert name == "kms"
            return "kms-client"

    def _session_factory():
        calls["session"] += 1
        return _FakeSession()

    monkeypatch.setattr(
        "kapitan.refs.secrets.awskms.boto3.session.Session", _session_factory
    )
    cached.awskms_obj = None

    assert awskms_obj() == "kms-client"
    assert awskms_obj() == "kms-client"
    assert calls["session"] == 1


def test_awskms_from_params_error_paths():
    with pytest.raises(ValueError, match="target_name not set"):
        AWSKMSSecret.from_params("data", SimpleNamespace(kwargs={"target_name": None}))

    cached.inv = SimpleNamespace(get_parameters=lambda _target: None)
    with pytest.raises(ValueError, match="target_inv not set"):
        AWSKMSSecret.from_params("data", SimpleNamespace(kwargs={"target_name": "t"}))

    with pytest.raises(RefError, match="target_name missing"):
        AWSKMSSecret.from_params("data", SimpleNamespace(kwargs={}))


def test_awskms_base64_update_and_encrypt_bytes(monkeypatch):
    encoded = AWSKMSSecret("data", "mock", encrypt=True, encode_base64=True)
    assert encoded.encoding == "base64"

    secret = AWSKMSSecret(b"ciphertext", "mock", encrypt=False)
    secret.encoding = "base64"

    monkeypatch.setattr(
        AWSKMSSecret,
        "reveal",
        lambda self: base64.b64encode(b"decoded").decode(),
    )
    captured = {}
    original_encrypt = AWSKMSSecret._encrypt

    def _capture_encrypt(self, data, key, encode_base64):
        captured["data"] = data
        captured["key"] = key
        captured["encode_base64"] = encode_base64
        self.data = b"reencrypted"
        self.key = key

    monkeypatch.setattr(AWSKMSSecret, "_encrypt", _capture_encrypt)

    assert secret.update_key("new-key") is True
    assert captured == {"data": "decoded", "key": "new-key", "encode_base64": True}
    assert secret.data == "cmVlbmNyeXB0ZWQ="

    original_encrypt(secret, b"bytes", "mock", encode_base64=False)
    assert secret.key == "mock"
