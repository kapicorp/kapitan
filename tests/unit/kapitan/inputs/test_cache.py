# Copyright 2025 The Kapitan Authors
# SPDX-FileCopyrightText: 2025 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from kapitan.errors import CompileError
from kapitan.inputs.cache import InputCache


@pytest.fixture
def cache_env(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_cache_home_prefers_xdg_cache_home(monkeypatch, tmp_path):
    home_dir = tmp_path / "home"
    xdg_cache_home = tmp_path / "xdg-cache"
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("XDG_CACHE_HOME", str(xdg_cache_home))

    cache = InputCache("test_input")

    assert cache.input_cache_home == f"{xdg_cache_home}/kapitan/test_input"


def test_cache_home_falls_back_to_home(cache_env):
    cache = InputCache("test_input")

    assert cache.input_cache_home == f"{cache_env}/.cache/kapitan/test_input"


def test_cache_home_missing_raises(monkeypatch):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    with pytest.raises(CompileError):
        InputCache("test_input")


def test_hash_paths_returns_expected_paths(cache_env):
    cache = InputCache("test_input")

    cached_path, cached_path_lock, sub_path = cache.hash_paths("abcdef123456")

    assert sub_path == Path(cache.input_cache_home, "ab")
    assert cached_path == Path(sub_path, "cdef123456")
    assert cached_path_lock == Path(f"{cached_path}.lock")


def test_set_and_get_round_trip(cache_env):
    cache = InputCache("test_input")
    inputs_hash = "abcdef123456"
    output_obj = {"a": 1, "b": 2}

    assert cache.get(inputs_hash) is None
    assert cache.set(inputs_hash, output_obj) == inputs_hash
    assert cache.get(inputs_hash) == output_obj
    assert cache.set(inputs_hash, {"c": 3}) == inputs_hash
    assert cache.get(inputs_hash) == output_obj


def test_set_value_and_get_key(cache_env):
    cache = InputCache("test_input")

    cache.set_value("key1", "value1")

    assert cache.get_key("key1") == "value1"


def test_hash_helpers_return_hasher_and_digest(cache_env, tmp_path):
    cache = InputCache("test_input")
    file_path = tmp_path / "input.txt"
    content = b"test content"
    file_path.write_bytes(content)

    hasher = cache.hash_object()
    hasher.update(content)
    assert hasher.hexdigest() == hashlib.blake2b(content, digest_size=32).hexdigest()
    with file_path.open("rb") as fp:
        assert (
            cache.hash_file_digest(fp).hexdigest()
            == hashlib.blake2b(content).hexdigest()
        )


def test_get_returns_none_for_cache_miss(cache_env):
    cache = InputCache("test_input")

    assert cache.get("nonexistenthash") is None


def test_cache_lock_contention_returns_none(cache_env):
    cache = InputCache("test_input")
    inputs_hash = "abcdef123456"
    output_obj = {"a": 1, "b": 2}

    _, cached_path_lock, sub_path = cache.hash_paths(inputs_hash)
    sub_path.mkdir(parents=True, exist_ok=True)
    cached_path_lock.touch()

    assert cache.get(inputs_hash) is None
    assert cache.set(inputs_hash, output_obj) is None


def test_set_propagates_file_exists_error(cache_env):
    cache = InputCache("test_input")

    with patch("pathlib.Path.rename", side_effect=FileExistsError):
        with pytest.raises(FileExistsError):
            cache.set("abcdef123456", {"a": 1, "b": 2})


def test_get_handles_file_not_found_during_read(cache_env):
    cache = InputCache("test_input")

    with patch("builtins.open", side_effect=FileNotFoundError):
        assert cache.get("abcdef123456") is None


def test_different_input_types_use_separate_directories(cache_env):
    cache_one = InputCache("input1")
    cache_two = InputCache("input2")

    assert cache_one.input_cache_home != cache_two.input_cache_home
    assert "input1" in cache_one.input_cache_home
    assert "input2" in cache_two.input_cache_home


def test_dump_and_load_output_round_trip(cache_env, tmp_path):
    cache = InputCache("test_input")
    file_path = tmp_path / "cache.bin"
    output_obj = {"a": 1, "b": 2}

    with file_path.open("wb") as fp:
        cache.dump_output(output_obj, fp)

    with file_path.open("rb") as fp:
        loaded_obj = cache.load_output(fp)

    assert loaded_obj == output_obj
