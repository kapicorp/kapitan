# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import builtins

import pytest

from kapitan.errors import CompileError
from kapitan.utils.hashing import dictionary_hash, directory_hash, sha256_string


def test_sha256_string():
    assert sha256_string("kapitan") == sha256_string("kapitan")


def test_directory_hash_covers_error_and_binary_paths(tmp_path, monkeypatch):
    with pytest.raises(OSError):
        directory_hash(str(tmp_path / "missing"))

    plain_file = tmp_path / "file.txt"
    plain_file.write_text("value", encoding="utf-8")
    with pytest.raises(OSError):
        directory_hash(str(plain_file))

    binary_dir = tmp_path / "binary"
    binary_dir.mkdir()
    (binary_dir / "payload.bin").write_bytes(b"\xff\xfe\xfd")
    digest = directory_hash(str(binary_dir))
    assert len(digest) == 64

    error_dir = tmp_path / "error"
    error_dir.mkdir()
    blocked_file = error_dir / "blocked.txt"
    blocked_file.write_text("data", encoding="utf-8")
    original_open = builtins.open

    def _raising_open(path, *args, **kwargs):
        if str(path).endswith("blocked.txt"):
            raise PermissionError("blocked")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _raising_open)
    with pytest.raises(CompileError):
        directory_hash(str(error_dir))


def test_dictionary_hash_is_stable():
    assert dictionary_hash({"a": 1, "b": 2}) == dictionary_hash({"b": 2, "a": 1})
