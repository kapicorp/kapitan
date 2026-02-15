# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import logging
import os
from types import SimpleNamespace

import pytest

from kapitan import cached
from kapitan.refs.base import RefError
from kapitan.refs.secrets.azkms import AzureKMSError, AzureKMSSecret, azkms_obj


class _FailingClient:
    def encrypt(self, *args, **kwargs):
        raise RuntimeError("boom")

    def decrypt(self, *args, **kwargs):
        raise RuntimeError("boom")


class _FakeAzureClient:
    def encrypt(self, algorithm, data):
        return SimpleNamespace(ciphertext=base64.b64encode(b"ciphertext"))

    def decrypt(self, algorithm, data):
        return SimpleNamespace(plaintext=b"plaintext")


@pytest.fixture(autouse=True)
def reset_cached_after():
    yield
    cached.reset_cache()


def test_azkms_write_reveal(tmp_path, ref_controller, revealer):
    tag = "?{azkms:secret/test}"
    ref_controller[tag] = AzureKMSSecret("mock", "mock")
    assert os.path.isfile(os.path.join(ref_controller.path, "secret/test"))

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text("I am a ?{azkms:secret/test} value")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))
    assert revealed == "I am a mock value"


def test_azkms_write_embedded_reveal(
    tmp_path, ref_controller_embedded, revealer_embedded
):
    tag = "?{azkms:secret/test}"
    ref_controller_embedded[tag] = AzureKMSSecret("mock", "mock")
    assert os.path.isfile(os.path.join(ref_controller_embedded.path, "secret/test"))
    ref_obj = ref_controller_embedded[tag]

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"I am a {ref_obj.compile()} value")

    revealed = revealer_embedded.reveal_raw_file(str(file_with_secret_tags))
    assert revealed == "I am a mock value"


def test_cli_secret_write_reveal_azkms(refs_cli, tmp_path, refs_path):
    test_secret_content = "mock"
    test_secret_file = tmp_path / "secret.txt"
    test_secret_file.write_text(test_secret_content)

    refs_cli.write("azkms:test_secret", test_secret_file, refs_path, key="mock")
    test_tag_content = "revealing: ?{azkms:test_secret}"
    test_tag_file = tmp_path / "tag.txt"
    test_tag_file.write_text(test_tag_content)
    stdout = refs_cli.reveal_file(test_tag_file, refs_path)
    assert stdout == f"revealing: {test_secret_content}"


def test_azkms_encrypt_error(monkeypatch):
    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.azkms_obj", lambda _key: _FailingClient()
    )
    with pytest.raises(AzureKMSError):
        AzureKMSSecret("data", "real", encrypt=True)


def test_azkms_decrypt_error(monkeypatch):
    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.azkms_obj", lambda _key: _FailingClient()
    )
    secret = AzureKMSSecret(b"data", "real", encrypt=False)
    secret.key = "real"
    with pytest.raises(AzureKMSError):
        secret._decrypt(base64.b64encode(b"cipher"), "real")


def test_azkms_encrypt_decrypt_and_update(monkeypatch):
    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.azkms_obj", lambda _key: _FakeAzureClient()
    )
    secret = AzureKMSSecret("data", "key", encrypt=True)
    assert secret.reveal() == "plaintext"
    assert secret.update_key("new-key") is True
    assert secret.key == "new-key"


def test_azkms_update_key_no_change():
    azkms = AzureKMSSecret(b"data", "mock", encrypt=False)
    assert azkms.update_key("mock") is False


def test_azkms_from_params():
    secrets = SimpleNamespace(azkms=SimpleNamespace(key="mock"))
    cached.inv = SimpleNamespace(
        get_parameters=lambda _target: SimpleNamespace(
            kapitan=SimpleNamespace(secrets=secrets)
        )
    )

    try:
        assert (
            AzureKMSSecret.from_params(
                "data", SimpleNamespace(kwargs={"target_name": "t"})
            ).key
            == "mock"
        )
    finally:
        cached.inv = None


def test_azkms_obj_parses_key_id_and_caches_client(monkeypatch):
    calls = {"key_client": 0, "crypto_client": 0}

    class _FakeKeyClient:
        def __init__(self, vault_url, credential):
            calls["key_client"] += 1
            self._vault_url = vault_url

        @staticmethod
        def get_key(name, version):
            return {"name": name, "version": version}

    class _FakeCryptoClient:
        def __init__(self, key, credential):
            calls["crypto_client"] += 1
            self.key = key

    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.DefaultAzureCredential", lambda: "cred"
    )
    monkeypatch.setattr("kapitan.refs.secrets.azkms.KeyClient", _FakeKeyClient)
    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.CryptographyClient", _FakeCryptoClient
    )

    cached.azkms_obj = None
    key_id = "https://kapitanbackend.vault.azure.net/keys/myKey/deadbeef"
    client = azkms_obj(key_id)
    assert isinstance(client, _FakeCryptoClient)
    assert calls["key_client"] == 1
    assert calls["crypto_client"] == 1

    assert azkms_obj(key_id) is client
    assert calls["crypto_client"] == 1

    cached.azkms_obj = None
    key_id_without_scheme = "kapitanbackend.vault.azure.net/keys/otherKey/version1"
    client2 = azkms_obj(key_id_without_scheme)
    assert isinstance(client2, _FakeCryptoClient)


def test_azkms_from_params_error_paths():
    with pytest.raises(ValueError, match="target_name not set"):
        AzureKMSSecret.from_params(
            "data", SimpleNamespace(kwargs={"target_name": None})
        )

    with pytest.raises(RefError, match="target_name missing"):
        AzureKMSSecret.from_params("data", SimpleNamespace(kwargs={}))


def test_azkms_base64_update_and_encrypt_bytes(monkeypatch):
    encoded = AzureKMSSecret("data", "mock", encrypt=True, encode_base64=True)
    assert encoded.encoding == "base64"

    secret = AzureKMSSecret(b"ciphertext", "mock", encrypt=False)
    secret.encoding = "base64"

    monkeypatch.setattr(
        AzureKMSSecret,
        "reveal",
        lambda self: base64.b64encode(b"decoded").decode(),
    )
    captured = {}
    original_encrypt = AzureKMSSecret._encrypt

    def _capture_encrypt(self, data, key, encode_base64):
        captured["data"] = data
        captured["key"] = key
        captured["encode_base64"] = encode_base64
        self.data = b"reencrypted"
        self.key = key

    monkeypatch.setattr(AzureKMSSecret, "_encrypt", _capture_encrypt)

    assert secret.update_key("new-key") is True
    assert captured == {"data": "decoded", "key": "new-key", "encode_base64": True}
    assert secret.data == "cmVlbmNyeXB0ZWQ="

    original_encrypt(secret, b"bytes", "mock", encode_base64=False)
    assert secret.key == "mock"


def test_azkms_obj_keeps_azure_logger_unchanged_in_debug_mode(monkeypatch):
    calls = {"set_level_calls": 0}

    class _FakeKeyClient:
        def __init__(self, vault_url, credential):
            self._vault_url = vault_url

        @staticmethod
        def get_key(name, version):
            return {"name": name, "version": version}

    class _FakeCryptoClient:
        def __init__(self, key, credential):
            self.key = key

    class _FakeAzureLogger:
        @staticmethod
        def setLevel(_level):
            calls["set_level_calls"] += 1

    real_get_logger = logging.getLogger

    def _get_logger(name=None):
        if name == "azure":
            return _FakeAzureLogger()
        return real_get_logger(name)

    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.logger.getEffectiveLevel", lambda: logging.DEBUG
    )
    monkeypatch.setattr("kapitan.refs.secrets.azkms.logging.getLogger", _get_logger)
    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.DefaultAzureCredential", lambda: "cred"
    )
    monkeypatch.setattr("kapitan.refs.secrets.azkms.KeyClient", _FakeKeyClient)
    monkeypatch.setattr(
        "kapitan.refs.secrets.azkms.CryptographyClient", _FakeCryptoClient
    )

    cached.azkms_obj = None
    client = azkms_obj("https://kapitanbackend.vault.azure.net/keys/myKey/deadbeef")
    assert isinstance(client, _FakeCryptoClient)
    assert calls["set_level_calls"] == 0
