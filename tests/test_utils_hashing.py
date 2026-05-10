#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for kapitan.utils.hashing (FR-009)."""

from kapitan.utils.hashing import dictionary_hash, get_entropy, sha256_string


class TestSha256String:
    def test_known_hash(self):
        result = sha256_string("hello")
        assert (
            result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    def test_empty_string(self):
        result = sha256_string("")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_same_input_same_output(self):
        assert sha256_string("kapitan") == sha256_string("kapitan")

    def test_different_inputs_differ(self):
        assert sha256_string("a") != sha256_string("b")


class TestDictionaryHash:
    def test_basic_dict(self):
        result = dictionary_hash({"key": "value"})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_key_order_independent(self):
        h1 = dictionary_hash({"a": 1, "b": 2})
        h2 = dictionary_hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_different_dicts_differ(self):
        h1 = dictionary_hash({"a": 1})
        h2 = dictionary_hash({"a": 2})
        assert h1 != h2

    def test_empty_dict(self):
        result = dictionary_hash({})
        assert isinstance(result, str)
        assert len(result) == 64


class TestGetEntropy:
    def test_all_same_characters_has_zero_entropy(self):
        assert get_entropy("aaaa") == 0.0

    def test_two_equal_symbols_has_one_bit_entropy(self):
        assert get_entropy("ab") == 1.0

    def test_entropy_is_nonnegative(self):
        assert get_entropy("kapitan") >= 0

    def test_returns_float(self):
        result = get_entropy("some string")
        assert isinstance(result, float)
