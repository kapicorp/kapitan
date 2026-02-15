# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from kapitan.refs.base import RefParams
from kapitan.refs.secrets.gpg import (
    GPG_TARGET_FINGERPRINTS,
    GPGError,
    GPGSecret,
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
