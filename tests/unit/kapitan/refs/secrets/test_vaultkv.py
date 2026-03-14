# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import copy
import logging
import os
from types import SimpleNamespace

import pytest
from hvac.exceptions import Forbidden

from kapitan import cached
from kapitan.inventory.model.references import (
    KapitanReferenceVaultKVConfig,
    VaultEngineTypes,
)
from kapitan.refs.base import RefError, RefParams
from kapitan.refs.secrets.vaultkv import VaultClient, VaultError, VaultSecret


logger = logging.getLogger(__name__)
pytestmark = pytest.mark.requires_vault


def test_token_authentication(vault_server):
    parameters = {"auth": "token"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)

    test_client = VaultClient(env)
    assert test_client.is_authenticated() is True
    test_client.adapter.close()


def test_token_authentication_envvar(vault_server, monkeypatch):
    parameters = {"auth": "token"}
    server_params = copy.deepcopy(vault_server.parameters)
    monkeypatch.setenv("VAULT_ADDR", server_params["addr"])
    del server_params["addr"]
    env = KapitanReferenceVaultKVConfig(**parameters, **server_params)

    test_client = VaultClient(env)
    assert test_client.is_authenticated() is True
    test_client.adapter.close()


def test_token_authentication_legacy_config(vault_server):
    server_params = copy.deepcopy(vault_server.parameters)
    parameters = {"auth": "token", "VAULT_ADDR": server_params["addr"]}
    del server_params["addr"]
    env = KapitanReferenceVaultKVConfig(**parameters, **server_params)

    test_client = VaultClient(env)
    assert test_client.is_authenticated() is True
    test_client.adapter.close()


def test_userpss_authentication(vault_server):
    parameters = {"auth": "userpass"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    test_client = VaultClient(env)
    assert test_client.is_authenticated() is True
    test_client.adapter.close()


def test_approle_authentication(vault_server):
    parameters = {"auth": "approle"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    test_client = VaultClient(env)
    assert test_client.is_authenticated() is True
    test_client.adapter.close()


def test_vault_write_reveal(vault_server, ref_controller, revealer, tmp_path):
    parameters = {"auth": "token", "mount": "secret"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    secret = "bar"

    tag = "?{vaultkv:secret/harleyquinn:secret:testpath:foo}"
    ref_controller[tag] = VaultSecret(
        secret.encode(),
        vault_params=env,
        mount_in_vault="secret",
        path_in_vault="testpath",
        key_in_vault="foo",
    )

    assert os.path.isfile(os.path.join(ref_controller.path, "secret/harleyquinn"))

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"File contents revealed: {tag}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))

    assert revealed == f"File contents revealed: {secret}"


def test_vault_reveal(vault_server, ref_controller, revealer, tmp_path):
    parameters = {"auth": "token"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    tag = "?{vaultkv:secret/batman}"
    secret = {"some_key": "something_secret"}
    client = VaultClient(env)
    client.secrets.kv.v2.create_or_update_secret(
        path="foo",
        secret=secret,
    )
    client.adapter.close()
    file_data = b"foo:some_key"
    ref_controller[tag] = VaultSecret(file_data, vault_params=env, encrypt=False)

    assert os.path.isfile(os.path.join(ref_controller.path, "secret/batman"))
    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"File contents revealed: {tag}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))

    assert revealed == f"File contents revealed: {secret['some_key']}"


def test_vault_reveal_missing_path(vault_server, ref_controller, revealer, tmp_path):
    tag = "?{vaultkv:secret/joker}"
    parameters = {"auth": "token"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    file_data = b"some_not_existing_path:some_key"
    ref_controller[tag] = VaultSecret(file_data, vault_params=env, encrypt=False)

    assert os.path.isfile(os.path.join(ref_controller.path, "secret/joker"))
    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"File contents revealed: {tag}")
    with pytest.raises(VaultError):
        revealer.reveal_raw_file(str(file_with_secret_tags))


def test_vault_reveal_missing_key(vault_server, ref_controller, revealer, tmp_path):
    tag = "?{vaultkv:secret/joker2}"
    parameters = {"auth": "token"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    file_data = b"foo:not_existing_key"
    ref_controller[tag] = VaultSecret(file_data, vault_params=env, encrypt=False)

    assert os.path.isfile(os.path.join(ref_controller.path, "secret/joker2"))
    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"File contents revealed: {tag}")
    with pytest.raises(VaultError):
        revealer.reveal_raw_file(str(file_with_secret_tags))


def test_vault_secret_from_params(vault_server, ref_controller):
    parameters = {"auth": "token", "mount": "secret"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    tag = "?{vaultkv:secret/harleyquinn2:secret:testpath:foo||random:str}"
    ref_controller[tag] = RefParams(vault_params=env)

    ref_obj = ref_controller[tag]
    assert ref_obj.vault_params.mount == "secret"
    assert ref_obj.path == "secret/harleyquinn2"


def test_vault_secret_from_params_base64(vault_server, ref_controller):
    parameters = {"auth": "token", "mount": "secret"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)
    tag = "?{vaultkv:secret/harleyquinn3:secret:testpath:foo||random:str|base64}"
    ref_controller[tag] = RefParams(vault_params=env)

    ref_obj = ref_controller[tag]
    assert ref_obj.vault_params.mount == "secret"
    assert ref_obj.path == "secret/harleyquinn3"
    assert ref_obj.encoding == "base64"


def test_multiple_secrets_in_path(vault_server, ref_controller, revealer, tmp_path):
    parameters = {"auth": "token"}
    env = KapitanReferenceVaultKVConfig(**parameters, **vault_server.parameters)

    secret = {"foo": "something_secret", "bar": "another_secret"}
    client = VaultClient(env)
    client.secrets.kv.v2.create_or_update_secret(path="foo", secret=secret)
    client.adapter.close()

    tag = "?{vaultkv:secret/batman}"
    file_data = b"foo:foo"
    ref_controller[tag] = VaultSecret(file_data, vault_params=env, encrypt=False)

    tag2 = "?{vaultkv:secret/robin}"
    file_data = b"foo:bar"
    ref_controller[tag2] = VaultSecret(file_data, vault_params=env, encrypt=False)

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"File contents revealed: {tag} {tag2}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))

    assert revealed == f"File contents revealed: {secret['foo']} {secret['bar']}"


class _KVV1:
    def __init__(self, store):
        self._store = store

    def read_secret(self, path, mount_point):
        return {"data": self._store.get(path, {})}


class _KVV2:
    def __init__(self, store):
        self._store = store

    def read_secret_version(self, path, mount_point, raise_on_deleted_version=False):
        return {"data": {"data": self._store.get(path, {})}}

    def create_or_update_secret(self, path, secret, mount_point):
        self._store[path] = secret


class _FakeVaultClient:
    def __init__(self, store):
        self.secrets = SimpleNamespace(
            kv=SimpleNamespace(v1=_KVV1(store), v2=_KVV2(store))
        )
        self.adapter = SimpleNamespace(close=lambda: None)


def test_vaultkv_encrypt_and_reveal_kv1(monkeypatch):
    store = {}
    client = _FakeVaultClient(store)
    monkeypatch.setattr("kapitan.refs.secrets.vaultkv.VaultClient", lambda _p: client)

    params = KapitanReferenceVaultKVConfig(
        auth="token", engine=VaultEngineTypes.KV, mount="mount"
    )
    secret = VaultSecret(
        b"data",
        params,
        mount_in_vault="mount",
        path_in_vault="path",
        key_in_vault="key",
    )

    assert base64.b64decode(secret.data).decode() == "path:key"
    assert secret.reveal() == "data"


def test_vaultkv_encrypt_and_reveal_kv2(monkeypatch):
    store = {}
    client = _FakeVaultClient(store)
    monkeypatch.setattr("kapitan.refs.secrets.vaultkv.VaultClient", lambda _p: client)

    params = KapitanReferenceVaultKVConfig(
        auth="token", engine=VaultEngineTypes.KV_V2, mount="mount"
    )
    secret = VaultSecret(
        b"data",
        params,
        mount_in_vault="mount",
        path_in_vault="path",
        key_in_vault="key",
    )

    assert secret.reveal() == "data"


def test_vaultkv_from_params_uses_target_defaults(monkeypatch):
    params = KapitanReferenceVaultKVConfig(auth="token", mount="secret")
    monkeypatch.setattr(
        cached,
        "inv",
        SimpleNamespace(
            get_parameters=lambda _target: SimpleNamespace(
                kapitan=SimpleNamespace(secrets=SimpleNamespace(vaultkv=params))
            )
        ),
    )

    ref_params = RefParams(
        target_name="dev",
        token="vaultkv:kapitan/path:::vault-key",
        encrypt=False,
    )

    secret = VaultSecret.from_params("payload", ref_params)
    assert isinstance(secret, VaultSecret)
    assert ref_params.kwargs["mount_in_vault"] == "secret"
    assert ref_params.kwargs["path_in_vault"] == "kapitan/path"
    assert ref_params.kwargs["key_in_vault"] == "vault-key"


def test_vaultkv_from_params_validates_token_and_required_fields(monkeypatch):
    class _SecretsWithoutVaultKV:
        @property
        def vaultkv(self):
            raise KeyError("vaultkv")

    monkeypatch.setattr(
        cached,
        "inv",
        SimpleNamespace(
            get_parameters=lambda _target: SimpleNamespace(
                kapitan=SimpleNamespace(secrets=_SecretsWithoutVaultKV())
            )
        ),
    )

    with pytest.raises(RefError, match="vaultkv parameters missing"):
        VaultSecret.from_params(
            "payload",
            RefParams(target_name="dev", token="vaultkv:path:::key", encrypt=False),
        )

    with pytest.raises(RefError, match="vaultkv parameters missing"):
        VaultSecret.from_params("payload", RefParams(target_name="dev", encrypt=False))

    monkeypatch.setattr(
        cached,
        "inv",
        SimpleNamespace(
            get_parameters=lambda _target: SimpleNamespace(
                kapitan=SimpleNamespace(
                    secrets=SimpleNamespace(
                        vaultkv=KapitanReferenceVaultKVConfig(
                            auth="token", mount="secret"
                        )
                    )
                )
            )
        ),
    )

    with pytest.raises(RefError, match="ref token is invalid"):
        VaultSecret.from_params(
            "payload",
            RefParams(target_name="dev", token="vaultkv:only:three", encrypt=False),
        )

    with pytest.raises(RefError, match="key is missing"):
        VaultSecret.from_params(
            "payload",
            RefParams(target_name="dev", token="vaultkv:path:::", encrypt=False),
        )


def test_vaultkv_reveal_with_base64_encoding_coerces_data_to_bytes(monkeypatch):
    params = KapitanReferenceVaultKVConfig(auth="token", mount="secret")
    secret = VaultSecret(b"path:key", params, encrypt=False)
    secret.encoding = "base64"

    monkeypatch.setattr(VaultSecret, "_decrypt", lambda self: "revealed")
    assert secret.reveal() == "revealed"
    assert isinstance(secret.data, bytes)


def test_vaultkv_encrypt_rejects_none_path():
    params = KapitanReferenceVaultKVConfig(auth="token", mount="secret")
    with pytest.raises(VaultError, match="Invalid path"):
        VaultSecret(
            b"data",
            params,
            mount_in_vault="secret",
            path_in_vault=None,
            key_in_vault="key",
        )


def test_vaultkv_encrypt_handles_forbidden_and_base64_mode(monkeypatch):
    class _ForbiddenKVV2:
        @staticmethod
        def read_secret_version(path, mount_point, raise_on_deleted_version=False):
            return {"data": {"data": {}}}

        @staticmethod
        def create_or_update_secret(path, secret, mount_point):
            raise Forbidden("denied")

    class _ClientForbidden:
        def __init__(self):
            self.secrets = SimpleNamespace(
                kv=SimpleNamespace(v1=_KVV1({}), v2=_ForbiddenKVV2())
            )
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaultkv.VaultClient",
        lambda _params: _ClientForbidden(),
    )

    params = KapitanReferenceVaultKVConfig(auth="token", mount="secret")
    secret = VaultSecret(b"path:key", params, encrypt=False)
    secret.path = "path"
    secret.mount = "secret"
    secret.key = "key"

    with pytest.raises(VaultError, match="Permission Denied"):
        secret._encrypt(b"data", encode_base64=False)

    store = {}
    monkeypatch.setattr(
        "kapitan.refs.secrets.vaultkv.VaultClient",
        lambda _params: _FakeVaultClient(store),
    )
    secret._encrypt(b"data", encode_base64=True)
    assert secret.encoding == "base64"
    assert base64.b64decode(secret.data).decode() == "path:key"


def test_vaultkv_decrypt_error_paths_and_base64_decoding(monkeypatch):
    params = KapitanReferenceVaultKVConfig(auth="token", mount="secret")

    class _NoopClient:
        def __init__(self):
            self.secrets = SimpleNamespace(
                kv=SimpleNamespace(v1=_KVV1({}), v2=_KVV2({}))
            )
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaultkv.VaultClient",
        lambda _params: _NoopClient(),
    )

    invalid_token_secret = VaultSecret(b"missing-separator", params, encrypt=False)
    with pytest.raises(RefError, match="secret should be stored"):
        invalid_token_secret._decrypt()

    class _ForbiddenKVV2:
        @staticmethod
        def read_secret_version(path, mount_point, raise_on_deleted_version=False):
            raise Forbidden("denied")

    class _ClientForbidden:
        def __init__(self):
            self.secrets = SimpleNamespace(
                kv=SimpleNamespace(v1=_KVV1({}), v2=_ForbiddenKVV2())
            )
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaultkv.VaultClient",
        lambda _params: _ClientForbidden(),
    )
    forbidden_secret = VaultSecret(b"path:key", params, encrypt=False)
    with pytest.raises(VaultError, match="Permission Denied"):
        forbidden_secret._decrypt()

    class _MissingKeyKVV2:
        @staticmethod
        def read_secret_version(path, mount_point, raise_on_deleted_version=False):
            return {"data": {"data": {}}}

    class _ClientMissingKey:
        def __init__(self):
            self.secrets = SimpleNamespace(
                kv=SimpleNamespace(v1=_KVV1({}), v2=_MissingKeyKVV2())
            )
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaultkv.VaultClient",
        lambda _params: _ClientMissingKey(),
    )
    missing_key_secret = VaultSecret(b"path:key", params, encrypt=False)
    with pytest.raises(VaultError, match="does not exist on Vault"):
        missing_key_secret._decrypt()

    class _EmptyValueKVV2:
        @staticmethod
        def read_secret_version(path, mount_point, raise_on_deleted_version=False):
            return {"data": {"data": {"key": ""}}}

    class _ClientEmptyValue:
        def __init__(self):
            self.secrets = SimpleNamespace(
                kv=SimpleNamespace(v1=_KVV1({}), v2=_EmptyValueKVV2())
            )
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaultkv.VaultClient",
        lambda _params: _ClientEmptyValue(),
    )
    empty_value_secret = VaultSecret(b"path:key", params, encrypt=False)
    with pytest.raises(VaultError, match="doesn't exist"):
        empty_value_secret._decrypt()

    class _Base64ValueKVV2:
        @staticmethod
        def read_secret_version(path, mount_point, raise_on_deleted_version=False):
            return {"data": {"data": {"key": base64.b64encode(b"plain").decode()}}}

    class _ClientBase64Value:
        def __init__(self):
            self.secrets = SimpleNamespace(
                kv=SimpleNamespace(v1=_KVV1({}), v2=_Base64ValueKVV2())
            )
            self.adapter = SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(
        "kapitan.refs.secrets.vaultkv.VaultClient",
        lambda _params: _ClientBase64Value(),
    )
    base64_secret = VaultSecret(b"path:key", params, encrypt=False)
    base64_secret.encoding = "base64"
    assert base64_secret._decrypt() == "plain"


def test_vaultkv_from_params_requires_target_name_and_token(monkeypatch):
    with pytest.raises(ValueError, match="target_name not set"):
        VaultSecret.from_params(
            "data",
            RefParams(target_name=None, token="vaultkv:path:mount:path:key"),
        )

    class _Inv:
        @staticmethod
        def get_parameters(_target):
            return type(
                "_Params",
                (),
                {
                    "kapitan": type(
                        "_Kapitan",
                        (),
                        {
                            "secrets": type(
                                "_Secrets",
                                (),
                                {
                                    "vaultkv": KapitanReferenceVaultKVConfig(
                                        auth="token"
                                    )
                                },
                            )()
                        },
                    )()
                },
            )()

    monkeypatch.setattr(cached, "inv", _Inv())
    with pytest.raises(RefError, match="vaultkv parameters missing"):
        VaultSecret.from_params("data", RefParams(target_name="dev", token=None))
