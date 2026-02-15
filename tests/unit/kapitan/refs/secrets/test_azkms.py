# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import os
from types import SimpleNamespace

import pytest

from kapitan import cached
from kapitan.refs.secrets.azkms import AzureKMSSecret


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


def test_azkms_update_key_no_change():
    azkms = AzureKMSSecret(b"data", "mock", encrypt=False)
    assert azkms.update_key("mock") is False
