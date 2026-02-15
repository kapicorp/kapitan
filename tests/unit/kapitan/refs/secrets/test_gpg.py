# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from kapitan import cached
from kapitan.errors import KapitanError
from kapitan.refs.base import RefError, RefParams
from kapitan.refs.secrets.gpg import (
    GPG_TARGET_FINGERPRINTS,
    GPGError,
    GPGSecret,
    fingerprint_non_expired,
)


EXAMPLE_FINGERPRINT = "D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C"


@pytest.fixture
def gpg_example_key():
    original = dict(GPG_TARGET_FINGERPRINTS)
    GPG_TARGET_FINGERPRINTS["KEY"] = EXAMPLE_FINGERPRINT
    yield EXAMPLE_FINGERPRINT
    GPG_TARGET_FINGERPRINTS.clear()
    GPG_TARGET_FINGERPRINTS.update(original)


@pytest.mark.usefixtures("setup_gpg_key")
def test_gpg_write_reveal(gpg_env, gpg_example_key, ref_controller, revealer, tmp_path):
    tag = "?{gpg:secret/sauce}"
    ref_controller[tag] = GPGSecret(
        "super secret value", [{"fingerprint": gpg_example_key}]
    )
    assert os.path.isfile(os.path.join(ref_controller.path, "secret/sauce"))

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text("I am a file with a ?{gpg:secret/sauce}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))
    assert revealed == "I am a file with a super secret value"


@pytest.mark.usefixtures("setup_gpg_key")
def test_gpg_write_embedded_reveal(
    gpg_env, gpg_example_key, ref_controller_embedded, revealer_embedded, tmp_path
):
    tag = "?{gpg:secret/sauce}"
    ref_controller_embedded[tag] = GPGSecret(
        "super secret value", [{"fingerprint": gpg_example_key}]
    )
    assert os.path.isfile(os.path.join(ref_controller_embedded.path, "secret/sauce"))
    ref_obj = ref_controller_embedded[tag]

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"I am a file with a {ref_obj.compile()}")
    revealed = revealer_embedded.reveal_raw_file(str(file_with_secret_tags))
    assert revealed == "I am a file with a super secret value"


@pytest.mark.usefixtures("setup_gpg_key")
def test_gpg_base64_write_reveal(
    gpg_env, gpg_example_key, ref_controller, revealer, tmp_path
):
    tag = "?{gpg:secret/sauce2}"
    ref_controller[tag] = GPGSecret(
        "super secret value", [{"fingerprint": gpg_example_key}], encode_base64=True
    )
    assert os.path.isfile(os.path.join(ref_controller.path, "secret/sauce2"))

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text("I am a file with a ?{gpg:secret/sauce2}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))
    assert revealed == "I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl"


@pytest.mark.usefixtures("setup_gpg_key")
def test_gpg_base64_write_embedded_reveal(
    gpg_env, gpg_example_key, ref_controller_embedded, revealer_embedded, tmp_path
):
    tag = "?{gpg:secret/sauce2}"
    ref_controller_embedded[tag] = GPGSecret(
        "super secret value", [{"fingerprint": gpg_example_key}], encode_base64=True
    )
    assert os.path.isfile(os.path.join(ref_controller_embedded.path, "secret/sauce2"))
    ref_obj = ref_controller_embedded[tag]

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text(f"I am a file with a {ref_obj.compile()}")
    revealed = revealer_embedded.reveal_raw_file(str(file_with_secret_tags))
    assert revealed == "I am a file with a c3VwZXIgc2VjcmV0IHZhbHVl"


@pytest.mark.usefixtures("setup_gpg_key")
def test_gpg_function_ed25519(
    gpg_env, gpg_example_key, ref_controller, revealer, tmp_path
):
    tag = "?{gpg:secret/ed25519||ed25519}"
    ref_controller[tag] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "secret/ed25519"))

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text("?{gpg:secret/ed25519}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))
    serialization.load_pem_private_key(
        revealed.encode(), password=None, backend=default_backend()
    )

    revealer._reveal_tag_without_subvar.cache_clear()
    tag = "?{gpg:secret/ed25519||ed25519}"
    ref_controller[tag] = RefParams()
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))

    private_key = serialization.load_pem_private_key(
        revealed.encode(), password=None, backend=default_backend()
    )

    tag_ed25519public = "?{gpg:secret/ed25519public||reveal:secret/ed25519|publickey}"
    ref_controller[tag_ed25519public] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "secret/ed25519"))

    file_with_secret_tags = tmp_path / "tags_pub.txt"
    file_with_secret_tags.write_text("?{gpg:secret/ed25519public}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))
    assert revealed.splitlines()[0] == "-----BEGIN PUBLIC KEY-----"
    assert private_key is not None


@pytest.mark.usefixtures("setup_gpg_key")
def test_gpg_function_rsa(gpg_env, gpg_example_key, ref_controller, revealer, tmp_path):
    tag = "?{gpg:secret/rsa||rsa}"
    ref_controller[tag] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "secret/rsa"))

    file_with_secret_tags = tmp_path / "tags.txt"
    file_with_secret_tags.write_text("?{gpg:secret/rsa}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))
    serialization.load_pem_private_key(
        revealed.encode(), password=None, backend=default_backend()
    )

    revealer._reveal_tag_without_subvar.cache_clear()
    tag = "?{gpg:secret/rsa||rsa:2048}"
    ref_controller[tag] = RefParams()
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))

    private_key = serialization.load_pem_private_key(
        revealed.encode(), password=None, backend=default_backend()
    )
    assert private_key.key_size == 2048

    tag_rsapublic = "?{gpg:secret/rsapublic||reveal:secret/rsa|rsapublic}"
    ref_controller[tag_rsapublic] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "secret/rsa"))

    file_with_secret_tags = tmp_path / "tags_pub.txt"
    file_with_secret_tags.write_text("?{gpg:secret/rsapublic}")
    revealed = revealer.reveal_raw_file(str(file_with_secret_tags))
    assert revealed.splitlines()[0] == "-----BEGIN PUBLIC KEY-----"


def test_gpg_from_params_uses_inventory_and_validates_required_fields(monkeypatch):
    recipients = [{"fingerprint": EXAMPLE_FINGERPRINT}]
    monkeypatch.setattr(
        cached,
        "inv",
        type(
            "_Inv",
            (),
            {
                "get_parameters": staticmethod(
                    lambda _target: type(
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
                                            "gpg": type(
                                                "_GPG", (), {"recipients": recipients}
                                            )()
                                        },
                                    )()
                                },
                            )()
                        },
                    )()
                )
            },
        )(),
    )

    secret = GPGSecret.from_params(
        b"encrypted",
        RefParams(target_name="dev", encrypt=False),
    )
    assert isinstance(secret, GPGSecret)
    assert secret.recipients == recipients

    with pytest.raises(KapitanError, match="parameters.kapitan.secrets not defined"):
        monkeypatch.setattr(
            cached,
            "inv",
            type(
                "_InvNoSecrets",
                (),
                {
                    "get_parameters": staticmethod(
                        lambda _target: type(
                            "_ParamsNoSecrets",
                            (),
                            {
                                "kapitan": type(
                                    "_KapitanNoSecrets", (), {"secrets": None}
                                )()
                            },
                        )()
                    )
                },
            )(),
        )
        GPGSecret.from_params(b"encrypted", RefParams(target_name="dev", encrypt=False))

    with pytest.raises(ValueError, match="target_name not set"):
        GPGSecret.from_params(b"encrypted", RefParams(target_name=None, encrypt=False))

    with pytest.raises(RefError, match="target_name missing"):
        GPGSecret.from_params(b"encrypted", RefParams(encrypt=False))


def test_gpg_update_recipients_reencrypts_and_handles_base64(monkeypatch):
    secret = GPGSecret(
        b"ciphertext",
        [{"fingerprint": EXAMPLE_FINGERPRINT}],
        encrypt=False,
    )
    secret.encoding = "base64"

    monkeypatch.setattr(
        GPGSecret,
        "reveal",
        lambda self: "bmV3LXBsYWludGV4dA==",  # base64("new-plaintext")
    )

    captured = {}

    def _fake_encrypt(self, data, fingerprints, encode_base64):
        captured["data"] = data
        captured["fingerprints"] = fingerprints
        captured["encode_base64"] = encode_base64
        self.data = b"reencrypted"
        self.recipients = [{"fingerprint": f} for f in fingerprints]

    monkeypatch.setattr(GPGSecret, "_encrypt", _fake_encrypt)

    updated = secret.update_recipients([{"fingerprint": "ABCD"}])
    assert updated is True
    assert captured == {
        "data": "new-plaintext",
        "fingerprints": ["ABCD"],
        "encode_base64": True,
    }
    assert secret.data == "cmVlbmNyeXB0ZWQ="


def test_gpg_update_recipients_reencrypts_without_base64_decoding(monkeypatch):
    secret = GPGSecret(
        b"ciphertext",
        [{"fingerprint": EXAMPLE_FINGERPRINT}],
        encrypt=False,
    )
    secret.encoding = "original"

    monkeypatch.setattr(GPGSecret, "reveal", lambda self: "plain-text")

    captured = {}

    def _fake_encrypt(self, data, fingerprints, encode_base64):
        captured["data"] = data
        captured["fingerprints"] = fingerprints
        captured["encode_base64"] = encode_base64
        self.data = b"reencrypted"
        self.recipients = [{"fingerprint": f} for f in fingerprints]

    monkeypatch.setattr(GPGSecret, "_encrypt", _fake_encrypt)

    updated = secret.update_recipients([{"fingerprint": "CHANGED"}])
    assert updated is True
    assert captured == {
        "data": "plain-text",
        "fingerprints": ["CHANGED"],
        "encode_base64": False,
    }


def test_gpg_encrypt_and_decrypt_raise_on_gpg_failures(monkeypatch):
    class _FailingGPG:
        @staticmethod
        def encrypt(_data, _fingerprints, sign=True, armor=False, **_kwargs):
            return type("_Result", (), {"ok": False, "status": "encrypt-failed"})()

        @staticmethod
        def decrypt(_data, **_kwargs):
            return type("_Result", (), {"ok": False, "status": "decrypt-failed"})()

    monkeypatch.setattr("kapitan.refs.secrets.gpg.gpg_obj", lambda: _FailingGPG())
    secret = GPGSecret(
        b"ciphertext", [{"fingerprint": EXAMPLE_FINGERPRINT}], encrypt=False
    )

    with pytest.raises(GPGError, match="encrypt-failed"):
        secret._encrypt("plaintext", [EXAMPLE_FINGERPRINT], encode_base64=False)

    with pytest.raises(GPGError, match="decrypt-failed"):
        secret._decrypt(b"ciphertext")


def test_fingerprint_non_expired_handles_invalid_expired_and_index_error(monkeypatch):
    class _GPGExpired:
        @staticmethod
        def list_keys(keys=()):
            return [
                {"fingerprint": "NO-EXPIRES"},
                {"fingerprint": "EXPIRED", "expires": "1"},
            ]

    monkeypatch.setattr("kapitan.refs.secrets.gpg.gpg_obj", lambda: _GPGExpired())
    monkeypatch.setattr("kapitan.refs.secrets.gpg.time.time", lambda: 10)
    with pytest.raises(GPGError, match="Could not find valid key"):
        fingerprint_non_expired("recipient@example.com")

    class _GPGIndexError:
        @staticmethod
        def list_keys(keys=()):
            raise IndexError("broken keyring")

    monkeypatch.setattr("kapitan.refs.secrets.gpg.gpg_obj", lambda: _GPGIndexError())
    with pytest.raises(IndexError, match="broken keyring"):
        fingerprint_non_expired("recipient@example.com")


def test_gpg_update_recipients_returns_false_when_fingerprints_match():
    secret = GPGSecret(
        b"ciphertext",
        [{"fingerprint": EXAMPLE_FINGERPRINT}],
        encrypt=False,
    )

    updated = secret.update_recipients([{"fingerprint": EXAMPLE_FINGERPRINT}])
    assert updated is False
