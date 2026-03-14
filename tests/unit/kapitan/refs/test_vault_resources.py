#!/usr/bin/env python3

from types import SimpleNamespace

import pytest

from kapitan.inventory.model.references import KapitanReferenceVaultCommon
from kapitan.refs.vault_resources import VaultClient, VaultError, get_env


def test_get_env_missing_cert_paths():
    params = KapitanReferenceVaultCommon(addr="http://vault", skip_verify=False)
    with pytest.raises(VaultError):
        get_env(params)


def test_get_env_with_cacert():
    params = KapitanReferenceVaultCommon(
        addr="http://vault", skip_verify=False, cacert="/tmp/ca.pem"
    )
    env = get_env(params)
    assert env["verify"] == "/tmp/ca.pem"


def test_get_env_skip_verify():
    params = KapitanReferenceVaultCommon(addr="http://vault", skip_verify=True)
    env = get_env(params)
    assert env["verify"] is False


def test_read_token_from_file_missing(tmp_path):
    client = VaultClient.__new__(VaultClient)
    with pytest.raises(VaultError):
        client.read_token_from_file(str(tmp_path / "missing"))


def test_read_token_from_file_empty(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("", encoding="utf-8")

    client = VaultClient.__new__(VaultClient)
    with pytest.raises(VaultError):
        client.read_token_from_file(str(token_file))


def test_authenticate_unsupported_auth():
    client = VaultClient.__new__(VaultClient)
    client.vault_params = KapitanReferenceVaultCommon(
        auth="unknown", addr="http://vault"
    )
    client.env = {}
    client.is_authenticated = lambda: True

    with pytest.raises(VaultError):
        client.authenticate()


def test_get_auth_token_reads_env(monkeypatch):
    client = VaultClient.__new__(VaultClient)
    client.vault_params = KapitanReferenceVaultCommon(auth="token", addr="http://vault")
    client.env = {}
    monkeypatch.setenv("VAULT_TOKEN", "token")

    client.get_auth_token()
    assert client.env["token"] == "token"


def test_get_env_accepts_dict_with_capath_and_client_cert():
    env = get_env(
        {
            "addr": "http://vault",
            "namespace": "ns",
            "skip_verify": False,
            "capath": "/tmp/ca",
            "client_key": "/tmp/key.pem",
            "client_cert": "/tmp/cert.pem",
        }
    )

    assert env["url"] == "http://vault"
    assert env["namespace"] == "ns"
    assert env["verify"] == "/tmp/ca"
    assert env["cert"] == ("/tmp/cert.pem", "/tmp/key.pem")


def test_get_env_skips_client_cert_when_key_or_cert_is_empty():
    params = KapitanReferenceVaultCommon(
        addr="http://vault",
        skip_verify=True,
        client_key="",
        client_cert="",
    )
    env = get_env(params)
    assert "cert" not in env


def test_read_token_from_file_returns_token(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("vault-token", encoding="utf-8")

    client = VaultClient.__new__(VaultClient)
    assert client.read_token_from_file(str(token_file)) == "vault-token"


def test_get_auth_token_falls_back_to_default_token_file(monkeypatch, tmp_path):
    default_token_file = tmp_path / ".vault-token"
    default_token_file.write_text("token-from-file", encoding="utf-8")

    client = VaultClient.__new__(VaultClient)
    client.vault_params = KapitanReferenceVaultCommon(auth="token", addr="http://vault")
    client.env = {}

    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setattr(
        "kapitan.refs.vault_resources.os.path.expanduser", lambda _v: str(tmp_path)
    )

    client.get_auth_token()
    assert client.env["token"] == "token-from-file"


def test_authenticate_ldap_uses_username_and_password(monkeypatch):
    login_calls = {}
    client = VaultClient.__new__(VaultClient)
    client.vault_params = KapitanReferenceVaultCommon(auth="ldap", addr="http://vault")
    client.env = {}
    client.get_auth_token = lambda: client.env.update({"token": "unused"})
    client._auth = SimpleNamespace(
        ldap=SimpleNamespace(
            login=lambda username, password: login_calls.update(
                {"username": username, "password": password}
            )
        )
    )
    client.is_authenticated = lambda: True

    monkeypatch.setenv("VAULT_USERNAME", "alice")
    monkeypatch.setenv("VAULT_PASSWORD", "pw")

    client.authenticate()
    assert login_calls == {"username": "alice", "password": "pw"}


def test_authenticate_github_uses_token():
    login_calls = {}
    client = VaultClient.__new__(VaultClient)
    client.vault_params = KapitanReferenceVaultCommon(
        auth="github", addr="http://vault"
    )
    client.env = {}
    client.get_auth_token = lambda: client.env.update({"token": "github-token"})
    client._auth = SimpleNamespace(
        github=SimpleNamespace(login=lambda token: login_calls.update({"token": token}))
    )
    client.is_authenticated = lambda: True

    client.authenticate()
    assert login_calls == {"token": "github-token"}


def test_authenticate_closes_adapter_when_not_authenticated():
    closed = {"value": False}
    client = VaultClient.__new__(VaultClient)
    client.vault_params = KapitanReferenceVaultCommon(auth="token", addr="http://vault")
    client.env = {}
    client.get_auth_token = lambda: client.env.update({"token": "token"})
    client._auth = SimpleNamespace()
    client._adapter = SimpleNamespace(
        token=None, close=lambda: closed.update({"value": True})
    )
    client.is_authenticated = lambda: False

    with pytest.raises(VaultError, match="Vault Authentication Error"):
        client.authenticate()

    assert closed["value"] is True
