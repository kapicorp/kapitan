#!/usr/bin/env python3

import io
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from kapitan.errors import KapitanError, RefError
from kapitan.refs.base import PlainRef
from kapitan.refs.base64 import Base64Ref
from kapitan.refs.cmd_parser import (
    handle_refs_command,
    ref_reveal,
    ref_write,
    secret_update,
    secret_update_validate,
)
from kapitan.refs.secrets.awskms import AWSKMSSecret
from kapitan.refs.secrets.azkms import AzureKMSSecret
from kapitan.refs.secrets.gkms import GoogleKMSSecret
from kapitan.refs.secrets.gpg import GPGSecret
from kapitan.refs.secrets.vaulttransit import VaultTransit


def _secrets_config(**overrides):
    base = {
        "gpg": None,
        "gkms": None,
        "awskms": None,
        "azkms": None,
        "azkey": False,
        "vaultkv": None,
        "vaulttransit": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_ref_write_base64(cmd_parser_args, cmd_parser_secret_file, ref_controller):
    secret_file = cmd_parser_secret_file(content="hello")
    args = cmd_parser_args(
        write="base64:my/secret",
        file=str(secret_file),
        base64=True,
    )

    ref_write(args, ref_controller)

    ref_path = Path(ref_controller.path) / "my" / "secret"
    assert ref_path.is_file()

    ref_obj = ref_controller["?{base64:my/secret}"]
    assert ref_obj.encoding == "base64"


def test_ref_write_invalid_token_type(
    cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file(content="hello")
    args = cmd_parser_args(write="invalid:secret", file=str(secret_file))

    with pytest.raises(KapitanError):
        ref_write(args, ref_controller)


def test_ref_reveal_tag(capsys, cmd_parser_args, ref_controller):
    tag = "?{plain:secret}"
    ref_controller[tag] = PlainRef(b"value")

    args = cmd_parser_args(tag=tag)
    ref_reveal(args, ref_controller)

    captured = capsys.readouterr()
    assert captured.out == "value"


def test_ref_write_invalid_type(
    cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file()
    args = cmd_parser_args(write="nope:secret", file=str(secret_file))

    with pytest.raises(KapitanError):
        ref_write(args, ref_controller)


def test_ref_write_gpg_requires_recipients(
    cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file()
    args = cmd_parser_args(write="gpg:secret", file=str(secret_file), recipients=[])

    with pytest.raises(KapitanError):
        ref_write(args, ref_controller)


@pytest.mark.parametrize("token", ["gkms", "awskms", "azkms"])
def test_ref_write_kms_requires_key(
    cmd_parser_args, cmd_parser_secret_file, ref_controller, token
):
    secret_file = cmd_parser_secret_file()
    args = cmd_parser_args(write=f"{token}:secret", file=str(secret_file))

    with pytest.raises(KapitanError):
        ref_write(args, ref_controller)


@pytest.mark.parametrize("token", ["vaultkv", "vaulttransit"])
def test_ref_write_vault_requires_auth(
    cmd_parser_args, cmd_parser_secret_file, ref_controller, token
):
    secret_file = cmd_parser_secret_file()
    args = cmd_parser_args(write=f"{token}:secret", file=str(secret_file))

    with pytest.raises(KapitanError):
        ref_write(args, ref_controller)


def test_ref_reveal_requires_input(cmd_parser_args, ref_controller):
    args = cmd_parser_args()
    with pytest.raises(SystemExit):
        ref_reveal(args, ref_controller)


def test_handle_refs_command_dispatches(monkeypatch, cmd_parser_args):
    calls = {}

    monkeypatch.setattr("kapitan.refs.cmd_parser.RefController", lambda _path: "refs")
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.ref_write",
        lambda _args, _controller: calls.setdefault("write", True),
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.secret_update",
        lambda _args, _controller: calls.setdefault("update", True),
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.secret_update_validate",
        lambda _args, _controller: calls.setdefault("validate", True),
    )

    handle_refs_command(cmd_parser_args(write="base64:secret", reveal=False))
    handle_refs_command(cmd_parser_args(update="gkms:secret"))
    handle_refs_command(cmd_parser_args(validate_targets=True))

    assert calls == {"write": True, "update": True, "validate": True}


def test_ref_write_base64_plain_env(
    cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file()

    ref_write(
        cmd_parser_args(write="base64:secret", file=str(secret_file)), ref_controller
    )
    ref_write(
        cmd_parser_args(write="plain:plain", file=str(secret_file)), ref_controller
    )
    ref_write(cmd_parser_args(write="env:env", file=str(secret_file)), ref_controller)

    ref_path = Path(ref_controller.path)
    for name, secret_type in (("secret", "base64"), ("plain", "plain"), ("env", "env")):
        payload = (ref_path / name).read_text(encoding="utf-8")
        assert yaml.safe_load(payload)["type"] == secret_type


def test_ref_write_from_stdin(monkeypatch, ref_controller, cmd_parser_args):
    monkeypatch.setattr("sys.stdin", io.StringIO("hello\nworld\n"))
    ref_write(cmd_parser_args(write="base64:stdin", file="-"), ref_controller)

    payload = (Path(ref_controller.path) / "stdin").read_text(encoding="utf-8")
    assert yaml.safe_load(payload)["type"] == "base64"


def test_ref_write_missing_file_exits(cmd_parser_args, ref_controller):
    with pytest.raises(SystemExit):
        ref_write(cmd_parser_args(write="base64:secret", file=None), ref_controller)


def test_ref_write_unicode_decode_error(
    cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file(
        name="secret.bin", content=b"\xff\xfe\xfd", binary=True
    )

    with pytest.raises(KapitanError):
        ref_write(
            cmd_parser_args(write="base64:secret", file=str(secret_file)),
            ref_controller,
        )


def test_ref_write_with_target_inventory(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_inventory,
    cmd_parser_secret_file,
    ref_controller,
):
    secret_file = cmd_parser_secret_file()
    inventory = cmd_parser_inventory(secrets=SimpleNamespace(), target_name="t")
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        write="base64:secret", file=str(secret_file), target_name="t"
    )
    ref_write(args, ref_controller)


def test_ref_write_vaultkv_builds_params(
    monkeypatch, cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file()

    captured = {}

    class _FakeVaultSecret:
        def __init__(self, data, vault_params, **kwargs):
            captured["data"] = data
            captured["vault_params"] = vault_params
            captured["kwargs"] = kwargs

    def _fake_setitem(self, key, value):
        captured["tag"] = key
        captured["value"] = value

    monkeypatch.setattr("kapitan.refs.cmd_parser.VaultSecret", _FakeVaultSecret)
    monkeypatch.setattr("kapitan.refs.base.RefController.__setitem__", _fake_setitem)

    args = cmd_parser_args(
        write="vaultkv:secret/path",
        file=str(secret_file),
        vault_auth="token",
        vault_key="key",
    )
    ref_write(args, ref_controller)

    assert captured["kwargs"]["path_in_vault"] == "secret/path"
    assert captured["kwargs"]["key_in_vault"] == "key"


def test_ref_write_vaulttransit_builds_params(
    monkeypatch, cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file()

    captured = {}

    class _FakeVaultTransit:
        def __init__(self, data, vault_params, **kwargs):
            captured["data"] = data
            captured["vault_params"] = vault_params

    def _fake_setitem(self, key, value):
        captured["tag"] = key
        captured["value"] = value

    monkeypatch.setattr("kapitan.refs.cmd_parser.VaultTransit", _FakeVaultTransit)
    monkeypatch.setattr("kapitan.refs.base.RefController.__setitem__", _fake_setitem)

    args = cmd_parser_args(
        write="vaulttransit:secret",
        file=str(secret_file),
        vault_auth="token",
    )
    ref_write(args, ref_controller)

    assert captured["tag"].startswith("?{vaulttransit:")


@pytest.mark.parametrize(
    ("token", "secret_cls"),
    [
        ("gkms:secret", GoogleKMSSecret),
        ("awskms:secret", AWSKMSSecret),
        ("azkms:secret", AzureKMSSecret),
    ],
)
def test_secret_update_kms_branches(cmd_parser_args, ref_controller, token, secret_cls):
    tag = f"?{{{token}}}"
    ref_controller[tag] = secret_cls(b"data", "mock", encrypt=False)

    args = cmd_parser_args(update=token, key="mock")
    secret_update(args, ref_controller)


def test_secret_update_requires_key(cmd_parser_args, ref_controller):
    ref_controller["?{gkms:secret}"] = GoogleKMSSecret(b"data", "mock", encrypt=False)

    with pytest.raises(KapitanError):
        secret_update(cmd_parser_args(update="gkms:secret", key=None), ref_controller)


@pytest.mark.parametrize("token", ["awskms", "gkms", "azkms"])
def test_ref_write_kms_success(
    cmd_parser_args, cmd_parser_secret_file, ref_controller, token
):
    secret_file = cmd_parser_secret_file()
    args = cmd_parser_args(write=f"{token}:secret", file=str(secret_file), key="mock")
    ref_write(args, ref_controller)
    assert (Path(ref_controller.path) / "secret").is_file()


def test_ref_reveal_file_path(tmp_path, ref_controller, capsys, cmd_parser_args):
    tag = "?{base64:secret}"
    ref_controller[tag] = Base64Ref(b"data")

    file_with_tag = tmp_path / "tags.txt"
    file_with_tag.write_text(f"value: {tag}", encoding="utf-8")

    args = cmd_parser_args(file=str(file_with_tag))
    ref_reveal(args, ref_controller)

    captured = capsys.readouterr()
    assert "value:" in captured.out


def test_ref_reveal_ref_file(ref_controller, capsys, cmd_parser_args):
    tag = "?{base64:secret}"
    ref_controller[tag] = Base64Ref(b"data")

    ref_file_path = Path(ref_controller.path) / "secret"
    args = cmd_parser_args(ref_file=str(ref_file_path))
    ref_reveal(args, ref_controller)

    captured = capsys.readouterr()
    assert captured.out


@pytest.mark.parametrize(
    ("token", "secret_cls"),
    [
        ("awskms", AWSKMSSecret),
        ("gkms", GoogleKMSSecret),
        ("azkms", AzureKMSSecret),
    ],
)
def test_secret_update_kms_no_change(
    cmd_parser_args, ref_controller, token, secret_cls
):
    token_value = f"{token}:secret"
    tag = f"?{{{token_value}}}"
    ref_controller[tag] = secret_cls(b"data", "mock", encrypt=False)

    args = cmd_parser_args(update=token_value, key="mock")
    secret_update(args, ref_controller)
    assert ref_controller[tag].key == "mock"


def test_secret_update_validate_mismatch(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_inventory,
    patch_cmd_parser_inventory,
    ref_controller,
):
    gpg_tag = "?{gpg:target/secret}"
    awskms_tag = "?{awskms:target/secret2}"
    gkms_tag = "?{gkms:target/secret3}"
    vaulttransit_tag = "?{vaulttransit:target/secret4}"

    vault_secret = VaultTransit(
        b"data", {"auth": "token", "crypto_key": "key"}, encrypt=False
    )

    class FakeVaultParams:
        def __init__(self, key):
            self._key = key

        def __getitem__(self, item):
            if item == "key":
                return self._key
            raise KeyError(item)

    vault_secret.vault_params = FakeVaultParams("old")

    secrets_map = {
        gpg_tag: GPGSecret(b"data", [{"fingerprint": "BBBB"}], encrypt=False),
        awskms_tag: AWSKMSSecret(b"data", "mock", encrypt=False),
        gkms_tag: GoogleKMSSecret(b"data", "mock", encrypt=False),
        vaulttransit_tag: vault_secret,
    }

    def _get_ref(self, key):
        return secrets_map[key]

    monkeypatch.setattr(type(ref_controller), "__getitem__", _get_ref)

    secrets = SimpleNamespace(
        gpg=SimpleNamespace(recipients=[{"fingerprint": "AAAA"}], key="mismatch"),
        gkms=SimpleNamespace(key="mock"),
        awskms=SimpleNamespace(key="other"),
        azkms=None,
        azkey=True,
        vaulttransit=SimpleNamespace(key="new"),
    )

    fake_inventory = cmd_parser_inventory(secrets=secrets)
    patch_cmd_parser_inventory(
        fake_inventory,
        {"target": [gpg_tag, awskms_tag, gkms_tag, vaulttransit_tag]},
    )

    args = cmd_parser_args(
        inventory_path="/tmp",
        refs_path=str(ref_controller.path),
        validate_targets=True,
    )

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(args, ref_controller)

    assert excinfo.value.code == 1


class _Secret:
    def __init__(self, key=None, vault_key=None):
        self.key = key
        self.vault_params = {"key": vault_key} if vault_key else None
        self.updated = False

    def update_key(self, _key):
        self.updated = True


class _FakeRefController:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value


def test_secret_update_validate_updates_keys(
    cmd_parser_args, cmd_parser_inventory, patch_cmd_parser_inventory
):
    gkms_tag = "?{gkms:target/secret}"
    awskms_tag = "?{awskms:target/secret2}"
    azkms_tag = "?{azkms:target/secret3}"
    vaulttransit_tag = "?{vaulttransit:target/secret4}"

    secrets_map = {
        gkms_tag: _Secret(key="old"),
        awskms_tag: _Secret(key="old"),
        azkms_tag: _Secret(key="old"),
        vaulttransit_tag: _Secret(vault_key="old"),
    }
    ref_controller = _FakeRefController(secrets_map)

    secrets = SimpleNamespace(
        gpg=SimpleNamespace(key="mismatch", recipients=[]),
        gkms=SimpleNamespace(key="new"),
        awskms=SimpleNamespace(key="new"),
        azkms=SimpleNamespace(key="new"),
        azkey=True,
        vaulttransit=SimpleNamespace(key="new"),
    )

    fake_inventory = cmd_parser_inventory(secrets=secrets)
    patch_cmd_parser_inventory(
        fake_inventory,
        {"target": [gkms_tag, awskms_tag, azkms_tag, vaulttransit_tag]},
    )

    args = cmd_parser_args(
        inventory_path="/tmp",
        refs_path="/tmp",
        validate_targets=False,
    )

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(args, ref_controller)

    assert excinfo.value.code == 0
    assert secrets_map[gkms_tag].updated is True
    assert secrets_map[awskms_tag].updated is True
    assert secrets_map[azkms_tag].updated is True
    assert secrets_map[vaulttransit_tag].updated is True


def test_handle_refs_command_dispatches_update_targets(monkeypatch, cmd_parser_args):
    calls = {}
    monkeypatch.setattr("kapitan.refs.cmd_parser.RefController", lambda _path: "refs")
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.secret_update_validate",
        lambda _args, _controller: calls.setdefault("validate", True),
    )

    handle_refs_command(cmd_parser_args(update_targets=True))
    assert calls == {"validate": True}


def test_ref_write_target_without_secrets_raises(
    monkeypatch, cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file()
    inventory = SimpleNamespace(
        get_parameters=lambda _target: (_ for _ in ()).throw(KeyError("missing"))
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        write="base64:secret",
        file=str(secret_file),
        target_name="target",
        inventory_path="/tmp/inventory",
    )
    with pytest.raises(KapitanError, match="parameters.kapitan.secrets not defined"):
        ref_write(args, ref_controller)


def test_ref_write_gpg_uses_target_recipients(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_secret_file,
    cmd_parser_inventory,
    ref_controller,
):
    secret_file = cmd_parser_secret_file()
    captured = {}

    class _FakeGPGSecret:
        def __init__(self, data, recipients, encode_base64=False):
            captured["data"] = data
            captured["recipients"] = recipients
            captured["encode_base64"] = encode_base64

    monkeypatch.setattr("kapitan.refs.cmd_parser.GPGSecret", _FakeGPGSecret)
    monkeypatch.setattr(
        "kapitan.refs.base.RefController.__setitem__",
        lambda _self, key, value: captured.update({"tag": key, "secret": value}),
    )

    inventory = cmd_parser_inventory(
        secrets=_secrets_config(
            gpg=SimpleNamespace(recipients=[{"name": "target-user"}])
        ),
        target_name="target",
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        write="gpg:secret",
        file=str(secret_file),
        target_name="target",
        inventory_path="/tmp/inventory",
        recipients=[],
    )
    ref_write(args, ref_controller)
    assert captured["recipients"] == [{"name": "target-user"}]


@pytest.mark.parametrize(
    ("token", "config_attr", "class_name"),
    [
        ("gkms", "gkms", "GoogleKMSSecret"),
        ("awskms", "awskms", "AWSKMSSecret"),
        ("azkms", "azkms", "AzureKMSSecret"),
    ],
)
def test_ref_write_kms_uses_target_key(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_secret_file,
    cmd_parser_inventory,
    ref_controller,
    token,
    config_attr,
    class_name,
):
    secret_file = cmd_parser_secret_file()
    captured = {}

    class _FakeKMSSecret:
        def __init__(self, data, key, encode_base64=False):
            captured["data"] = data
            captured["key"] = key
            captured["encode_base64"] = encode_base64

    monkeypatch.setattr(f"kapitan.refs.cmd_parser.{class_name}", _FakeKMSSecret)
    monkeypatch.setattr(
        "kapitan.refs.base.RefController.__setitem__",
        lambda _self, key, value: captured.update({"tag": key, "secret": value}),
    )

    secrets = _secrets_config()
    setattr(secrets, config_attr, SimpleNamespace(key="inventory-key"))
    inventory = cmd_parser_inventory(secrets=secrets, target_name="target")
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        write=f"{token}:secret",
        file=str(secret_file),
        target_name="target",
        inventory_path="/tmp/inventory",
        key=None,
    )
    ref_write(args, ref_controller)
    assert captured["key"] == "inventory-key"


def test_ref_write_vaultkv_uses_target_mount(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_secret_file,
    cmd_parser_inventory,
    ref_controller,
):
    secret_file = cmd_parser_secret_file()
    captured = {}

    class _FakeVaultSecret:
        def __init__(self, data, vault_params, **kwargs):
            captured["data"] = data
            captured["vault_params"] = vault_params
            captured["kwargs"] = kwargs

    monkeypatch.setattr("kapitan.refs.cmd_parser.VaultSecret", _FakeVaultSecret)
    monkeypatch.setattr(
        "kapitan.refs.base.RefController.__setitem__",
        lambda _self, key, value: captured.update({"tag": key, "secret": value}),
    )

    inventory = cmd_parser_inventory(
        secrets=_secrets_config(
            vaultkv=SimpleNamespace(auth="token", mount="inventory-mount")
        ),
        target_name="target",
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        write="vaultkv:service/path",
        file=str(secret_file),
        target_name="target",
        inventory_path="/tmp/inventory",
        vault_key="payload",
    )
    ref_write(args, ref_controller)
    assert captured["kwargs"]["mount_in_vault"] == "inventory-mount"
    assert captured["kwargs"]["path_in_vault"] == "service/path"


def test_ref_write_vaultkv_requires_key(
    cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file()
    args = cmd_parser_args(
        write="vaultkv:service/path",
        file=str(secret_file),
        vault_auth="token",
        vault_key=None,
    )
    with pytest.raises(RefError, match="vaultkv: key is missing"):
        ref_write(args, ref_controller)


def test_ref_write_vaulttransit_uses_target_config(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_secret_file,
    cmd_parser_inventory,
    ref_controller,
):
    secret_file = cmd_parser_secret_file()
    captured = {}

    class _FakeVaultTransit:
        def __init__(self, data, vault_params, **kwargs):
            captured["data"] = data
            captured["vault_params"] = vault_params
            captured["kwargs"] = kwargs

    monkeypatch.setattr("kapitan.refs.cmd_parser.VaultTransit", _FakeVaultTransit)
    monkeypatch.setattr(
        "kapitan.refs.base.RefController.__setitem__",
        lambda _self, key, value: captured.update({"tag": key, "secret": value}),
    )

    inventory = cmd_parser_inventory(
        secrets=_secrets_config(vaulttransit=SimpleNamespace(auth="token")),
        target_name="target",
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        write="vaulttransit:service/path",
        file=str(secret_file),
        target_name="target",
        inventory_path="/tmp/inventory",
    )
    ref_write(args, ref_controller)
    assert captured["vault_params"].auth == "token"


def test_ref_write_plain_and_env_base64(
    cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file(content="hello")
    ref_write(
        cmd_parser_args(write="plain:plain-secret", file=str(secret_file), base64=True),
        ref_controller,
    )
    ref_write(
        cmd_parser_args(write="env:env-secret", file=str(secret_file), base64=True),
        ref_controller,
    )

    plain_payload = yaml.safe_load(
        (Path(ref_controller.path) / "plain-secret").read_text(encoding="utf-8")
    )
    env_payload = yaml.safe_load(
        (Path(ref_controller.path) / "env-secret").read_text(encoding="utf-8")
    )
    assert plain_payload["encoding"] == "base64"
    assert env_payload["type"] == "env"


def test_secret_update_target_without_secrets_raises(
    monkeypatch, cmd_parser_args, cmd_parser_inventory, ref_controller
):
    inventory = cmd_parser_inventory(secrets=None, target_name="target")
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        update="gkms:secret",
        target_name="target",
        inventory_path="/tmp/inventory",
    )
    with pytest.raises(KapitanError, match="parameters.kapitan.secrets not defined"):
        secret_update(args, ref_controller)


def test_secret_update_invalid_token_type(cmd_parser_args, ref_controller):
    with pytest.raises(KapitanError, match="Invalid token type"):
        secret_update(cmd_parser_args(update="invalid:secret"), ref_controller)


def test_secret_update_gpg_uses_target_recipients(
    monkeypatch, cmd_parser_args, ref_controller
):
    class _FakeGPGSecret:
        def __init__(self):
            self.recipients = None

        def update_recipients(self, recipients):
            self.recipients = recipients

    fake_secret = _FakeGPGSecret()
    captured = {}

    monkeypatch.setattr(
        type(ref_controller), "__getitem__", lambda _self, _key: fake_secret
    )
    monkeypatch.setattr(
        type(ref_controller),
        "__setitem__",
        lambda _self, key, value: captured.update({"key": key, "value": value}),
    )

    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.KapitanReferenceConfig",
        lambda: _secrets_config(
            gpg=SimpleNamespace(recipients=[{"name": "target-user"}])
        ),
    )

    args = cmd_parser_args(
        update="gpg:secret",
        recipients=["cli-user"],
    )
    secret_update(args, ref_controller)
    assert fake_secret.recipients == [{"name": "target-user"}]
    assert captured["key"] == "?{gpg:secret}"


@pytest.mark.parametrize(
    ("token", "config_attr"),
    [
        ("gkms", "gkms"),
        ("awskms", "awskms"),
        ("azkms", "azkms"),
    ],
)
def test_secret_update_kms_uses_target_key(
    monkeypatch,
    cmd_parser_args,
    ref_controller,
    token,
    config_attr,
):
    class _FakeKMSSecret:
        def __init__(self):
            self.updated_key = None

        def update_key(self, key):
            self.updated_key = key

    fake_secret = _FakeKMSSecret()
    monkeypatch.setattr(
        type(ref_controller), "__getitem__", lambda _self, _key: fake_secret
    )
    monkeypatch.setattr(
        type(ref_controller), "__setitem__", lambda *_args, **_kwargs: None
    )

    secrets = _secrets_config()
    setattr(secrets, config_attr, SimpleNamespace(key="inventory-key"))
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.KapitanReferenceConfig", lambda: secrets
    )

    args = cmd_parser_args(
        update=f"{token}:secret",
        key="cli-key",
    )
    secret_update(args, ref_controller)
    assert fake_secret.updated_key == "inventory-key"


def test_secret_update_invalid_token_family_exits(cmd_parser_args, ref_controller):
    with pytest.raises(SystemExit):
        secret_update(cmd_parser_args(update="base64:secret"), ref_controller)


def test_secret_update_gpg_requires_recipients(cmd_parser_args, ref_controller):
    with pytest.raises(KapitanError, match="No GPG recipients specified"):
        secret_update(
            cmd_parser_args(update="gpg:secret", recipients=[]), ref_controller
        )


@pytest.mark.parametrize("token", ["awskms", "azkms"])
def test_secret_update_additional_kms_requires_key(
    cmd_parser_args, ref_controller, token
):
    with pytest.raises(KapitanError, match="No KMS key specified"):
        secret_update(
            cmd_parser_args(update=f"{token}:secret", key=None), ref_controller
        )


def test_ref_reveal_from_stdin(capsys, monkeypatch, cmd_parser_args, ref_controller):
    ref_controller["?{plain:stdin/secret}"] = PlainRef(b"stdin-value")
    monkeypatch.setattr("sys.stdin", io.StringIO("?{plain:stdin/secret}\n"))

    ref_reveal(cmd_parser_args(file="-"), ref_controller)
    assert capsys.readouterr().out == "stdin-value\n"


def test_ref_reveal_wraps_lookup_errors(monkeypatch, cmd_parser_args, ref_controller):
    def _raise_lookup_error(_self, _path):
        raise KeyError("missing")

    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.Revealer.reveal_path", _raise_lookup_error
    )

    with pytest.raises(KapitanError, match="Reveal failed for file /tmp/missing"):
        ref_reveal(cmd_parser_args(file="/tmp/missing"), ref_controller)


def test_secret_update_validate_target_without_secrets_raises(
    cmd_parser_args, cmd_parser_inventory, patch_cmd_parser_inventory, ref_controller
):
    inventory = cmd_parser_inventory(secrets=None)
    patch_cmd_parser_inventory(inventory, {"target": ["?{gpg:target/secret}"]})
    args = cmd_parser_args(
        inventory_path="/tmp/inventory",
        refs_path=str(ref_controller.path),
        validate_targets=True,
    )
    with pytest.raises(KapitanError, match="parameters.kapitan.secrets not defined"):
        secret_update_validate(args, ref_controller)


def test_secret_update_validate_skips_missing_configs_and_unknown_types(
    cmd_parser_args, cmd_parser_inventory, patch_cmd_parser_inventory
):
    token_paths = [
        "?{gpg:target/secret}",
        "?{gkms:target/secret}",
        "?{vaulttransit:target/secret}",
        "?{awskms:target/secret}",
        "?{azkms:target/secret}",
        "?{plain:target/secret}",
    ]
    inventory = cmd_parser_inventory(
        secrets=_secrets_config(azkey=False),
        target_name="target",
    )
    patch_cmd_parser_inventory(inventory, {"target": token_paths})

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(
            cmd_parser_args(
                inventory_path="/tmp/inventory",
                refs_path="/tmp/refs",
                validate_targets=False,
            ),
            _FakeRefController({}),
        )
    assert excinfo.value.code == 0


def test_secret_update_validate_updates_gpg_recipients(
    monkeypatch, cmd_parser_args, cmd_parser_inventory, patch_cmd_parser_inventory
):
    class _GPGSecretState:
        def __init__(self):
            self.recipients = [{"fingerprint": "BBBB"}]
            self.updated_with = None

        def update_recipients(self, recipients):
            self.updated_with = recipients
            self.recipients = recipients

    secret = _GPGSecretState()
    token = "?{gpg:target/secret}"

    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.lookup_fingerprints",
        lambda recipients: [recipient["fingerprint"] for recipient in recipients],
    )

    inventory = cmd_parser_inventory(
        secrets=_secrets_config(
            gpg=SimpleNamespace(key="unused", recipients=[{"fingerprint": "AAAA"}])
        ),
        target_name="target",
    )
    patch_cmd_parser_inventory(inventory, {"target": [token]})

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(
            cmd_parser_args(
                inventory_path="/tmp/inventory",
                refs_path="/tmp/refs",
                validate_targets=False,
            ),
            _FakeRefController({token: secret}),
        )
    assert excinfo.value.code == 0
    assert secret.updated_with == [{"fingerprint": "AAAA"}]


def test_secret_update_validate_azkms_mismatch_in_validate_mode(
    cmd_parser_args, cmd_parser_inventory, patch_cmd_parser_inventory
):
    token = "?{azkms:target/secret}"
    inventory = cmd_parser_inventory(
        secrets=_secrets_config(
            gpg=SimpleNamespace(key="unused", recipients=[]),
            azkey=True,
            azkms=SimpleNamespace(key="new"),
        ),
        target_name="target",
    )
    patch_cmd_parser_inventory(inventory, {"target": [token]})

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(
            cmd_parser_args(
                inventory_path="/tmp/inventory",
                refs_path="/tmp/refs",
                validate_targets=True,
            ),
            _FakeRefController({token: _Secret(key="old")}),
        )
    assert excinfo.value.code == 1


def test_handle_refs_command_with_no_action_performs_no_dispatch(
    monkeypatch, cmd_parser_args
):
    calls = {}

    monkeypatch.setattr("kapitan.refs.cmd_parser.RefController", lambda _path: "refs")
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.ref_write",
        lambda *_args, **_kwargs: calls.setdefault("write", True),
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.ref_reveal",
        lambda *_args, **_kwargs: calls.setdefault("reveal", True),
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.secret_update",
        lambda *_args, **_kwargs: calls.setdefault("update", True),
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.secret_update_validate",
        lambda *_args, **_kwargs: calls.setdefault("validate", True),
    )

    handle_refs_command(cmd_parser_args())
    assert calls == {}


def test_ref_reveal_empty_tag_writes_nothing(capsys, cmd_parser_args, ref_controller):
    ref_reveal(cmd_parser_args(tag=""), ref_controller)
    assert capsys.readouterr().out == ""


def test_ref_write_vaultkv_uses_cli_mount_when_inventory_mount_is_empty(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_secret_file,
    cmd_parser_inventory,
    ref_controller,
):
    secret_file = cmd_parser_secret_file()
    captured = {}

    class _FakeVaultSecret:
        def __init__(self, data, vault_params, **kwargs):
            captured["data"] = data
            captured["vault_params"] = vault_params
            captured["kwargs"] = kwargs

    monkeypatch.setattr("kapitan.refs.cmd_parser.VaultSecret", _FakeVaultSecret)
    monkeypatch.setattr(
        "kapitan.refs.base.RefController.__setitem__",
        lambda _self, key, value: captured.update({"tag": key, "secret": value}),
    )

    inventory = cmd_parser_inventory(
        secrets=_secrets_config(vaultkv=SimpleNamespace(auth="token", mount="")),
        target_name="target",
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    args = cmd_parser_args(
        write="vaultkv:service/path",
        file=str(secret_file),
        target_name="target",
        inventory_path="/tmp/inventory",
        vault_mount="cli-mount",
        vault_key="payload",
    )
    ref_write(args, ref_controller)
    assert captured["kwargs"]["mount_in_vault"] == "cli-mount"


def test_secret_update_with_target_inventory_uses_cli_key_when_inventory_not_loaded(
    monkeypatch, cmd_parser_args, cmd_parser_inventory, ref_controller
):
    class _FakeSecret:
        def __init__(self):
            self.updated_key = None

        def update_key(self, key):
            self.updated_key = key

    fake_secret = _FakeSecret()
    monkeypatch.setattr(
        type(ref_controller), "__getitem__", lambda _self, _key: fake_secret
    )
    monkeypatch.setattr(
        type(ref_controller), "__setitem__", lambda *_args, **_kwargs: None
    )

    inventory = cmd_parser_inventory(
        secrets=_secrets_config(gkms=SimpleNamespace(key="inventory-key")),
        target_name="target",
    )
    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.get_inventory", lambda _path: inventory
    )

    secret_update(
        cmd_parser_args(
            update="gkms:secret",
            target_name="target",
            inventory_path="/tmp/inventory",
            key="cli-key",
        ),
        ref_controller,
    )
    assert fake_secret.updated_key == "cli-key"


@pytest.mark.parametrize(
    ("target_fingerprints", "secret_fingerprints"),
    [
        (["AAAA", "BBBB"], ["AAAA"]),
        (["AAAA"], ["AAAA", "BBBB"]),
    ],
)
def test_secret_update_validate_gpg_mismatch_logs_add_remove_variants(
    monkeypatch,
    cmd_parser_args,
    cmd_parser_inventory,
    patch_cmd_parser_inventory,
    target_fingerprints,
    secret_fingerprints,
):
    class _GPGSecretState:
        def __init__(self, recipients):
            self.recipients = [{"fingerprint": f} for f in recipients]

    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.lookup_fingerprints",
        lambda recipients: [recipient["fingerprint"] for recipient in recipients],
    )

    token = "?{gpg:target/secret}"
    inventory = cmd_parser_inventory(
        secrets=_secrets_config(
            gpg=SimpleNamespace(
                key="unused",
                recipients=[
                    {"fingerprint": fingerprint} for fingerprint in target_fingerprints
                ],
            )
        ),
        target_name="target",
    )
    patch_cmd_parser_inventory(inventory, {"target": [token]})

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(
            cmd_parser_args(
                inventory_path="/tmp/inventory",
                refs_path="/tmp/refs",
                validate_targets=True,
            ),
            _FakeRefController({token: _GPGSecretState(secret_fingerprints)}),
        )
    assert excinfo.value.code == 1


def test_secret_update_validate_matching_keys_skip_update_branches(
    cmd_parser_args, cmd_parser_inventory, patch_cmd_parser_inventory
):
    gkms_tag = "?{gkms:target/secret}"
    vaulttransit_tag = "?{vaulttransit:target/transit}"
    awskms_tag = "?{awskms:target/aws}"
    azkms_tag = "?{azkms:target/azure}"

    refs = {
        gkms_tag: _Secret(key="same-key"),
        vaulttransit_tag: _Secret(vault_key="same-key"),
        awskms_tag: _Secret(key="same-key"),
        azkms_tag: _Secret(key="same-key"),
    }
    ref_controller = _FakeRefController(refs)

    inventory = cmd_parser_inventory(
        secrets=_secrets_config(
            gpg=SimpleNamespace(key="same-key", recipients=[]),
            gkms=SimpleNamespace(key="same-key"),
            vaulttransit=SimpleNamespace(key="same-key"),
            awskms=SimpleNamespace(key="same-key"),
            azkey=True,
            azkms=SimpleNamespace(key="same-key"),
        ),
        target_name="target",
    )
    patch_cmd_parser_inventory(
        inventory,
        {"target": [gkms_tag, vaulttransit_tag, awskms_tag, azkms_tag]},
    )

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(
            cmd_parser_args(
                inventory_path="/tmp/inventory",
                refs_path="/tmp/refs",
                validate_targets=False,
            ),
            ref_controller,
        )
    assert excinfo.value.code == 0
    assert refs[gkms_tag].updated is False
    assert refs[vaulttransit_tag].updated is False
    assert refs[awskms_tag].updated is False
    assert refs[azkms_tag].updated is False


def test_secret_update_validate_matching_gpg_recipients_skip_mismatch_branch(
    monkeypatch, cmd_parser_args, cmd_parser_inventory, patch_cmd_parser_inventory
):
    class _GPGSecretState:
        def __init__(self, recipients):
            self.recipients = [{"fingerprint": f} for f in recipients]

    monkeypatch.setattr(
        "kapitan.refs.cmd_parser.lookup_fingerprints",
        lambda recipients: [recipient["fingerprint"] for recipient in recipients],
    )

    token = "?{gpg:target/secret}"
    inventory = cmd_parser_inventory(
        secrets=_secrets_config(
            gpg=SimpleNamespace(
                key="unused",
                recipients=[
                    {"fingerprint": "AAAA"},
                    {"fingerprint": "BBBB"},
                ],
            )
        ),
        target_name="target",
    )
    patch_cmd_parser_inventory(inventory, {"target": [token]})

    with pytest.raises(SystemExit) as excinfo:
        secret_update_validate(
            cmd_parser_args(
                inventory_path="/tmp/inventory",
                refs_path="/tmp/refs",
                validate_targets=True,
            ),
            _FakeRefController({token: _GPGSecretState(["AAAA", "BBBB"])}),
        )

    assert excinfo.value.code == 0


def test_ref_write_handles_unmatched_reference_type_fallthrough(
    monkeypatch, cmd_parser_args, cmd_parser_secret_file, ref_controller
):
    secret_file = cmd_parser_secret_file(content="value")

    class _FakeTypes:
        GPG = "gpg"
        GKMS = "gkms"
        AWSKMS = "awskms"
        AZKMS = "azkms"
        BASE64 = "base64"
        VAULTKV = "vaultkv"
        VAULTTRANSIT = "vaulttransit"
        PLAIN = "plain"
        ENV = "env"

        @staticmethod
        def __call__(_value):
            return "unmatched-ref-type"

    monkeypatch.setattr("kapitan.refs.cmd_parser.KapitanReferencesTypes", _FakeTypes())
    ref_write(
        cmd_parser_args(write="base64:secret", file=str(secret_file)), ref_controller
    )

    assert not (Path(ref_controller.path) / "secret").exists()
