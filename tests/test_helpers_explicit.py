#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the explicit (global-free) paths of leaf helpers.

These exercise make_reveal_maybe and null_presenter through their explicit
inputs, proving they work without mutating kapitan.cached. The cache-reading
shims remain covered by the existing characterization tests.
"""

import unittest

import yaml

# kapitan.utils and kapitan.jinja2_filters have a circular import; importing
# utils first (it sorts before jinja2_filters) resolves the load order.
from kapitan import utils
from kapitan.jinja2_filters import make_reveal_maybe


PrettyDumper = utils.PrettyDumper


class _FakeRevealer:
    def __init__(self):
        self.calls = []

    def reveal_raw(self, ref_tag):
        self.calls.append(ref_tag)
        return f"revealed:{ref_tag}"


class MakeRevealMaybeTest(unittest.TestCase):
    """make_reveal_maybe binds an explicit reveal flag + revealer (no globals)."""

    def test_reveal_true_calls_revealer(self):
        revealer = _FakeRevealer()
        filt = make_reveal_maybe(reveal=True, revealer=revealer)
        self.assertEqual(filt("?{gpg:foo}"), "revealed:?{gpg:foo}")
        self.assertEqual(revealer.calls, ["?{gpg:foo}"])

    def test_reveal_false_passes_through(self):
        revealer = _FakeRevealer()
        filt = make_reveal_maybe(reveal=False, revealer=revealer)
        self.assertEqual(filt("?{gpg:foo}"), "?{gpg:foo}")
        self.assertEqual(revealer.calls, [])


class _EmptyNullDumper(PrettyDumper):
    yaml_dump_null_as_empty = True


class _ExplicitNullDumper(PrettyDumper):
    yaml_dump_null_as_empty = False


class NullPresenterExplicitTest(unittest.TestCase):
    """null_presenter reads the flag off the dumper without touching cached."""

    def test_dumper_flag_true_omits_value(self):
        out = yaml.dump({"a": None, "b": 1}, Dumper=_EmptyNullDumper)
        self.assertEqual(out, "a:\nb: 1\n")

    def test_dumper_flag_false_emits_null(self):
        out = yaml.dump({"a": None, "b": 1}, Dumper=_ExplicitNullDumper)
        self.assertEqual(out, "a: null\nb: 1\n")
