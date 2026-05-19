#!/usr/bin/env python3
# Copyright 2026 The Kapitan Authors
# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for filtering None values from multi-document YAML streams.

Related to https://github.com/kapicorp/kapitan/issues/1396 where helm charts
with comments before ``---`` produce empty YAML documents that kubectl rejects.
"""

import io
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

from kapitan import cached


class TestNullFilter:
    """None values in multi-document streams should be filtered out."""

    @pytest.fixture(autouse=True)
    def _reset_cached(self):
        prev_args = cached.args
        prev_inv = cached.inv
        cached.inv = {"t": {"parameters": {}}}
        yield
        cached.args = prev_args
        cached.inv = prev_inv

    def _make_compiling_file(self, buf):
        from kapitan.inputs.base import CompilingFile

        buf.name = "<test>"
        ref_controller = MagicMock()
        with patch("kapitan.inputs.base.Revealer") as Revealer:
            revealer = Revealer.return_value
            revealer.compile_obj.side_effect = lambda o, **kw: o
            revealer.reveal_obj.side_effect = lambda o: o
            return CompilingFile(buf, ref_controller, target_name="t", indent=2)

    def test_filters_none_from_multi_doc_pyyaml(self):
        """A list containing None and dicts should omit the None documents."""
        cached.args = Namespace()
        buf = io.StringIO()
        self._make_compiling_file(buf).write_yaml([None, {"a": 1}, None])
        docs = list(yaml.safe_load_all(buf.getvalue()))
        assert docs == [{"a": 1}]

    def test_skips_write_when_all_none_pyyaml(self):
        """A list containing only None should result in no output."""
        cached.args = Namespace()
        buf = io.StringIO()
        self._make_compiling_file(buf).write_yaml([None, None])
        assert buf.getvalue() == ""

    def test_preserves_none_in_nested_structure_pyyaml(self):
        """None values inside a mapping should still be emitted as null/empty."""
        cached.args = Namespace()
        buf = io.StringIO()
        self._make_compiling_file(buf).write_yaml({"key": None, "other": "value"})
        doc = yaml.safe_load(buf.getvalue())
        assert doc == {"key": None, "other": "value"}
