# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import logging
from types import SimpleNamespace

import pytest
from hvac.exceptions import Forbidden, InvalidPath

from kapitan import cached
from kapitan.inventory.model.references import KapitanReferenceVaultTransitConfig
from kapitan.refs.base import RefError, RefParams
from kapitan.refs.secrets.vaulttransit import VaultBackend, VaultError, VaultTransit
from kapitan.refs.vault_resources import VaultClient
from tests.support.vault_server import VaultTransitServer


logger = logging.getLogger(__name__)
pytestmark = pytest.mark.requires_vault


@pytest.fixture(scope="module")
def vault_transit_env():
    server = VaultTransitServer()
    server.vault_client.secrets.transit.create_key(name="hvac_key")
    server.vault_client.secrets.transit.create_key(name="hvac_updated_key")

    parameters = {"auth": "token", "crypto_key": "hvac_key"}
    env = dict(**parameters, **server.parameters)
    client = VaultClient(env)

    yield server, client

    client.adapter.close()
    server.close_container()


def test_vault_transit_enc_data(vault_transit_env):
    server, client = vault_transit_env
    parameters = {"auth": "token", "crypto_key": "hvac_key"}
    env = dict(**parameters, **server.parameters)

    file_data = "foo:some_random_value"
    vault_transit_obj = VaultTransit(file_data, env)

    data = base64.b64decode(vault_transit_obj.data.encode())

    response = client.secrets.transit.decrypt_data(
        name="hvac_key", mount_point="transit", ciphertext=data.decode()
    )

    plaintext = base64.b64decode(response["data"]["plaintext"])
    assert plaintext == file_data.encode()


def test_vault_transit_dec_data(vault_transit_env):
    server, client = vault_transit_env
    parameters = {"auth": "token", "crypto_key": "hvac_key", "always_latest": False}
    env = dict(**parameters, **server.parameters)
    file_data = "foo:some_random_value"
    vault_transit_obj = VaultTransit(file_data, env)

    b64_file_data = base64.b64encode(file_data.encode())
    response = client.secrets.transit.encrypt_data(
        name="hvac_key", mount_point="transit", plaintext=b64_file_data.decode()
    )

    data = response["data"]["ciphertext"].encode()
    dec_data = vault_transit_obj._decrypt(data)
    assert dec_data == file_data


def test_vault_transit_update_key(vault_transit_env):
    server, client = vault_transit_env
    parameters = {"auth": "token", "crypto_key": "hvac_key", "always_latest": False}
    env = dict(**parameters, **server.parameters)
    file_data = "foo:some_random_value"
    vault_transit_obj = VaultTransit(file_data, env)

    data = base64.b64decode(vault_transit_obj.data.encode())

    assert vault_transit_obj.update_key("hvac_updated_key") is True
    updated_ciphertext = base64.b64decode(vault_transit_obj.data)
    assert data != updated_ciphertext

    response = client.secrets.transit.decrypt_data(
        name="hvac_key", mount_point="transit", ciphertext=data.decode()
    )

    plaintext = base64.b64decode(response["data"]["plaintext"])
    assert plaintext == file_data.encode()


class _FailingTransit:
    def encrypt_data(self, *args, **kwargs):
        raise Forbidden("nope")


class _FailingClient:
    def __init__(self):
        self.secrets = SimpleNamespace(transit=_FailingTransit())
        self.adapter = SimpleNamespace(close=lambda: None)


class _NoopClient:
    def __init__(self):
        self.secrets = SimpleNamespace(transit=SimpleNamespace())
        self.adapter = SimpleNamespace(close=lambda: None)


def test_reveal_invalid_base64_raises_exit():
    params = KapitanReferenceVaultTransitConfig(auth="token", crypto_key="key")
    secret = VaultTransit(b"valid", params, encrypt=False)
    secret.data = "not-base64%%%"

    with pytest.raises(SystemExit):
        secret.reveal()


def test_reveal_missing_crypto_key(monkeypatch):
    params = KapitanReferenceVaultTransitConfig(auth="token", crypto_key=None)
    payload = base64.b64encode(b"cipher")
    secret = VaultTransit(payload, params, encrypt=False)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaulttransit.VaultClient",
        lambda *_args, **_kwargs: _NoopClient(),
    )

    with pytest.raises(RefError):
        secret.reveal()


def test_encrypt_forbidden(monkeypatch):
    params = KapitanReferenceVaultTransitConfig(auth="token", crypto_key="key")
    monkeypatch.setattr(
        "kapitan.refs.secrets.vaulttransit.VaultClient",
        lambda *_args, **_kwargs: _FailingClient(),
    )

    with pytest.raises(VaultError):
        VaultTransit("data", params, encrypt=True)


class _FakeTransit:
    def __init__(self):
        self.rewrap_called = False

    def encrypt_data(self, name, mount_point, plaintext):
        ciphertext = base64.b64encode(b"cipher").decode("ascii")
        return {"data": {"ciphertext": ciphertext}}

    def decrypt_data(self, name, mount_point, ciphertext):
        plaintext = base64.b64encode(b"plain").decode("ascii")
        return {"data": {"plaintext": plaintext}}

    def rewrap_data(self, name, mount_point, ciphertext):
        self.rewrap_called = True
        return {"data": {"ciphertext": ciphertext}}


class _FakeClient:
    def __init__(self):
        self.secrets = SimpleNamespace(transit=_FakeTransit())
        self.adapter = SimpleNamespace(close=lambda: None)


def test_vaulttransit_encrypt_reveal_update(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(
        "kapitan.refs.secrets.vaulttransit.VaultClient", lambda _p: client
    )

    params = KapitanReferenceVaultTransitConfig(
        auth="token", crypto_key="key", always_latest=True
    )
    secret = VaultTransit("data", params, encrypt=True)

    assert secret.reveal() == "plain"
    assert client.secrets.transit.rewrap_called is True
    assert secret.update_key("new-key") is True


def test_vaulttransit_from_params_and_from_path(monkeypatch, tmp_path):
    params = KapitanReferenceVaultTransitConfig(auth="token", crypto_key="key")
    monkeypatch.setattr(
        cached,
        "inv",
        SimpleNamespace(
            get_parameters=lambda _target: SimpleNamespace(
                kapitan=SimpleNamespace(secrets=SimpleNamespace(vaulttransit=params))
            )
        ),
    )

    secret = VaultTransit.from_params(
        b"payload", RefParams(target_name="dev", encrypt=False)
    )
    assert isinstance(secret, VaultTransit)
    assert secret.vault_params.crypto_key == "key"

    with pytest.raises(RefError, match="vaulttransit parameters missing"):
        VaultTransit.from_params(b"payload", RefParams(encrypt=False))

    assert VaultTransit.from_path(str(tmp_path / "missing-ref")) is None


def test_vaulttransit_update_key_edge_cases(monkeypatch):
    params = KapitanReferenceVaultTransitConfig(auth="token", crypto_key="old")
    secret = VaultTransit(b"payload", params, encrypt=False)

    assert secret.update_key("old") is False

    secret.encoding = "base64"
    monkeypatch.setattr(
        VaultTransit,
        "reveal",
        lambda self: base64.b64encode(b"decoded").decode(),
    )
    captured = {}

    def _capture_encrypt(self, data, key, encode_base64):
        captured["data"] = data
        captured["key"] = key
        captured["encode_base64"] = encode_base64
        self.data = b"cipher"

    monkeypatch.setattr(VaultTransit, "_encrypt", _capture_encrypt)
    assert secret.update_key("new") is True
    assert captured == {"data": "decoded", "key": "new", "encode_base64": True}


def test_vaulttransit_encrypt_and_decrypt_error_branches(monkeypatch):
    params = KapitanReferenceVaultTransitConfig(auth="token", crypto_key="key")
    secret = VaultTransit(b"payload", params, encrypt=False)

    class _EncryptInvalidTransit:
        @staticmethod
        def encrypt_data(name, mount_point, plaintext):
            raise InvalidPath("missing")

    class _DecryptForbiddenTransit:
        @staticmethod
        def decrypt_data(name, mount_point, ciphertext):
            raise Forbidden("forbidden")

    class _DecryptInvalidTransit:
        @staticmethod
        def decrypt_data(name, mount_point, ciphertext):
            raise InvalidPath("missing")

    class _ClientEncryptInvalid:
        def __init__(self):
            self.secrets = SimpleNamespace(transit=_EncryptInvalidTransit())
            self.adapter = SimpleNamespace(close=lambda: None)

    class _ClientDecryptForbidden:
        def __init__(self):
            self.secrets = SimpleNamespace(transit=_DecryptForbiddenTransit())
            self.adapter = SimpleNamespace(close=lambda: None)

    class _ClientDecryptInvalid:
        def __init__(self):
            self.secrets = SimpleNamespace(transit=_DecryptInvalidTransit())
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaulttransit.VaultClient",
        lambda _params: _ClientEncryptInvalid(),
    )
    with pytest.raises(VaultError, match="does not exist"):
        secret._encrypt("payload", "key", encode_base64=True)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaulttransit.VaultClient",
        lambda _params: _ClientDecryptForbidden(),
    )
    with pytest.raises(VaultError, match="Permission Denied"):
        secret._decrypt(b"cipher")

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaulttransit.VaultClient",
        lambda _params: _ClientDecryptInvalid(),
    )
    with pytest.raises(VaultError, match="does not exist"):
        secret._decrypt(b"cipher")


def test_vaulttransit_dump_backend_and_encrypt_bytes(monkeypatch, tmp_path):
    class _SuccessTransit:
        @staticmethod
        def encrypt_data(name, mount_point, plaintext):
            return {"data": {"ciphertext": "vault:v1:abc"}}

    class _SuccessClient:
        def __init__(self):
            self.secrets = SimpleNamespace(transit=_SuccessTransit())
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaulttransit.VaultClient",
        lambda _params: _SuccessClient(),
    )

    params = KapitanReferenceVaultTransitConfig(auth="token", crypto_key="key")
    secret = VaultTransit(b"payload", params, encrypt=False)
    secret._encrypt(b"already-bytes", "key", encode_base64=True)
    dumped = secret.dump()

    assert dumped["type"]
    assert dumped["encoding"] == "original"
    assert dumped["vault_params"]["crypto_key"] == "key"

    backend = VaultBackend(str(tmp_path / "refs"))
    assert str(backend.type_name) == "vaulttransit"


def test_vaulttransit_from_params_requires_target_name():
    with pytest.raises(ValueError, match="target_name not set"):
        VaultTransit.from_params("data", RefParams(target_name=None))
