# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import logging
from types import SimpleNamespace

import pytest
from hvac.exceptions import Forbidden

from kapitan.inventory.model.references import KapitanReferenceVaultTransitConfig
from kapitan.refs.secrets.vaulttransit import VaultTransit
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
