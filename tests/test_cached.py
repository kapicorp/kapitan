#!/usr/bin/env python3

# Copyright 2025 The Kapitan Authors
# SPDX-FileCopyrightText: 2025 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the kapitan.cached module."""

from argparse import Namespace

import pytest

from kapitan import cached


class TestResetCache:
    """Tests for reset_cache function."""

    def test_reset_cache_clears_all_variables(self):
        """Test that reset_cache clears all global cache variables."""
        # Set some values
        cached.inv = {"key": "value"}
        cached.global_inv = {"global": "data"}
        cached.inv_cache = {"cache": "entry"}
        cached.inv_sources = {"source1", "source2"}
        cached.gpg_obj = "gpg"
        cached.gkms_obj = "gkms"
        cached.awskms_obj = "awskms"
        cached.azkms_obj = "azkms"
        cached.dot_kapitan = {"dot": "kapitan"}
        cached.ref_controller_obj = "ref"
        cached.revealer_obj = "revealer"

        # Reset
        cached.reset_cache()

        # Verify all cleared
        assert cached.inv == {}
        assert cached.global_inv == {}
        assert cached.inv_cache == {}
        assert cached.inv_sources == set()
        assert cached.gpg_obj is None
        assert cached.gkms_obj is None
        assert cached.awskms_obj is None
        assert cached.azkms_obj is None
        assert cached.dot_kapitan == {}
        assert cached.ref_controller_obj is None
        assert cached.revealer_obj is None

    def test_reset_cache_preserves_args(self):
        """Test that reset_cache does not reset args."""
        original_args = cached.args
        cached.args = Namespace(test="value")

        cached.reset_cache()

        # args should not be reset
        assert cached.args == Namespace(test="value")


class TestFromDict:
    """Tests for from_dict function."""

    def test_from_dict_restores_all_variables(self):
        """Test that from_dict correctly restores cache from dictionary."""
        cache_dict = {
            "inv": {"inv_key": "inv_value"},
            "global_inv": {"global_key": "global_value"},
            "inv_cache": {"cache_key": "cache_value"},
            "inv_sources": {"source1", "source2"},
            "gpg_obj": "test_gpg",
            "gkms_obj": "test_gkms",
            "awskms_obj": "test_awskms",
            "azkms_obj": "test_azkms",
            "dot_kapitan": {"dot_key": "dot_value"},
            "ref_controller_obj": "test_ref",
            "revealer_obj": "test_revealer",
            "args": Namespace(test_arg="test_value"),
        }

        cached.from_dict(cache_dict)

        assert cached.inv == {"inv_key": "inv_value"}
        assert cached.global_inv == {"global_key": "global_value"}
        assert cached.inv_cache == {"cache_key": "cache_value"}
        assert cached.inv_sources == {"source1", "source2"}
        assert cached.gpg_obj == "test_gpg"
        assert cached.gkms_obj == "test_gkms"
        assert cached.awskms_obj == "test_awskms"
        assert cached.azkms_obj == "test_azkms"
        assert cached.dot_kapitan == {"dot_key": "dot_value"}
        assert cached.ref_controller_obj == "test_ref"
        assert cached.revealer_obj == "test_revealer"
        assert cached.args == Namespace(test_arg="test_value")


class TestAsDict:
    """Tests for as_dict function."""

    def test_as_dict_serializes_all_variables(self):
        """Test that as_dict returns dictionary with all cache variables."""
        # Setup some test values
        cached.reset_cache()
        cached.inv = {"test": "inv"}
        cached.global_inv = {"test": "global"}
        cached.gpg_obj = "test_gpg"

        result = cached.as_dict()

        assert isinstance(result, dict)
        assert result["inv"] == {"test": "inv"}
        assert result["global_inv"] == {"test": "global"}
        assert result["gpg_obj"] == "test_gpg"
        assert "inv_cache" in result
        assert "inv_sources" in result
        assert "args" in result

    def test_as_dict_round_trip(self):
        """Test that as_dict -> from_dict preserves state."""
        # Setup initial state
        cached.reset_cache()
        cached.inv = {"key1": "value1"}
        cached.gpg_obj = "gpg_test"
        cached.inv_sources = {"source1"}

        # Serialize
        state_dict = cached.as_dict()

        # Modify state
        cached.inv = {"different": "value"}
        cached.gpg_obj = None

        # Restore
        cached.from_dict(state_dict)

        # Verify restoration
        assert cached.inv == {"key1": "value1"}
        assert cached.gpg_obj == "gpg_test"
        assert cached.inv_sources == {"source1"}


class TestResetInv:
    """Tests for reset_inv function."""

    def test_reset_inv_clears_only_inv(self):
        """Test that reset_inv only clears inv, not other variables."""
        cached.inv = {"key": "value"}
        cached.global_inv = {"global": "value"}
        cached.inv_cache = {"cache": "value"}

        cached.reset_inv()

        assert cached.inv == {}
        assert cached.global_inv == {"global": "value"}
        assert cached.inv_cache == {"cache": "value"}


class TestModuleVariables:
    """Tests for module-level variable initialization."""

    def test_initial_state(self):
        """Test that module variables have correct initial state."""
        cached.reset_cache()

        assert isinstance(cached.inv, dict)
        assert isinstance(cached.global_inv, dict)
        assert isinstance(cached.inventory_global_kadet, dict)
        assert isinstance(cached.inv_cache, dict)
        assert isinstance(cached.dot_kapitan, dict)
        assert isinstance(cached.inv_sources, set)
        assert isinstance(cached.args, Namespace)
