#!/usr/bin/env python3
# Copyright 2024 The Kapitan Authors
# SPDX-FileCopyrightText: 2024 The Kapitan Authors <kapitan-admins@googlegroups.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for the --yaml-use-rapidyaml fast emit path.

These tests cover:

  * the standalone ``kapitan.yaml_ryml.dump`` API (round-trip, key sorting,
    ambiguous-string quoting, multiline styles, control-char fallback),
  * the integration with ``CompilingFile.write_yaml`` (PyYAML vs ryml
    output dispatch via ``cached.args.yaml_use_rapidyaml``),
  * the one-time startup warning emitted from ``trigger_compile`` when the
    flag is set but the ``rapidyaml`` package is not installed.
"""

import io
import logging
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

from kapitan import cached


# rapidyaml is an optional dependency; skip the whole module if it's missing
# rather than testing a no-op fallback (which is covered separately by
# ``test_warning_logged_when_rapidyaml_missing`` via monkeypatch).
ryml_pkg = pytest.importorskip("ryml")
from kapitan import yaml_ryml  # noqa: E402  (import after importorskip)


# ---------------------------------------------------------------------------
# Standalone emitter tests
# ---------------------------------------------------------------------------
class TestRymlDump:
    """Direct tests against ``kapitan.yaml_ryml.dump``."""

    def test_basic_roundtrip(self):
        """Every supported scalar type round-trips to an equal Python object."""
        obj = {
            "string": "hello",
            "int": 42,
            "float": 3.14,
            "true": True,
            "false": False,
            "none": None,
            "list": [1, "two", 3.0, None],
            "nested": {"a": {"b": "c"}},
        }
        buf = io.StringIO()
        yaml_ryml.dump(obj, buf)
        assert yaml.safe_load(buf.getvalue()) == obj

    @pytest.mark.parametrize(
        "ambiguous_string",
        ["true", "false", "yes", "no", "Yes", "null", "123", "-1", ".5", "1e10"],
    )
    def test_ambiguous_strings_are_quoted(self, ambiguous_string):
        """Strings that would round-trip as another type must be quoted."""
        obj = {"key": ambiguous_string}
        buf = io.StringIO()
        yaml_ryml.dump(obj, buf)
        loaded = yaml.safe_load(buf.getvalue())
        assert loaded == obj
        assert isinstance(loaded["key"], str), (
            f"{ambiguous_string!r} was re-parsed as {type(loaded['key']).__name__}: "
            f"{buf.getvalue()!r}"
        )

    def test_keys_are_sorted_alphabetically(self):
        """Mapping keys are emitted in sorted order for deterministic output."""
        buf = io.StringIO()
        yaml_ryml.dump({"zebra": 1, "apple": 2, "mango": 3}, buf)
        lines = [line for line in buf.getvalue().splitlines() if line.strip()]
        assert lines == ["apple: 2", "mango: 3", "zebra: 1"]

    def test_determinism_across_shuffled_insertion_orders(self):
        """Same content, different dict insertion orders => identical bytes."""
        import random

        canonical = {
            "zoo": 0,
            "apple": 1,
            "banana": 2,
            "mango": 3,
            "cherry": 4,
            "date": 5,
        }
        keys = list(canonical)
        outputs = set()
        for _ in range(20):
            random.shuffle(keys)
            shuffled = {k: canonical[k] for k in keys}
            buf = io.StringIO()
            yaml_ryml.dump(shuffled, buf)
            outputs.add(buf.getvalue())
        assert len(outputs) == 1

    def test_mixed_type_keys_fall_back_to_insertion_order(self):
        """Incomparable mixed-type keys must not crash (matches PyYAML)."""
        buf = io.StringIO()
        # str < int comparison raises TypeError; we must keep insertion order.
        yaml_ryml.dump({"a": 1, 2: "b", "c": 3}, buf)
        # No assertion on order, just that emission succeeded and round-trips.
        assert yaml.safe_load(buf.getvalue()) == {"a": 1, 2: "b", "c": 3}

    @pytest.mark.parametrize("style", ["literal", "folded", "double-quotes"])
    def test_multiline_string_styles(self, style):
        """Each supported multiline style produces parser-equivalent output."""
        obj = {"m": "line1\nline2\nline3"}
        buf = io.StringIO()
        yaml_ryml.dump(obj, buf, multiline_style=style)
        out = buf.getvalue()
        assert yaml.safe_load(out) == obj
        # Sanity: the emitted block should reflect the chosen indicator.
        indicators = {"literal": "|", "folded": ">", "double-quotes": '"'}
        assert indicators[style] in out

    def test_dump_null_as_empty(self):
        obj = {"x": None, "y": 1}
        buf = io.StringIO()
        yaml_ryml.dump(obj, buf, dump_null_as_empty=True)
        assert buf.getvalue() == "x: \ny: 1\n"
        assert yaml.safe_load(buf.getvalue()) == obj

    def test_multi_doc_emission(self):
        """A top-level list with ``multi_doc=True`` emits one YAML doc per item."""
        items = [{"a": 1}, {"b": 2}, "scalar"]
        buf = io.StringIO()
        yaml_ryml.dump(items, buf, multi_doc=True)
        assert list(yaml.safe_load_all(buf.getvalue())) == items

    def test_large_string_does_not_crash(self):
        """Arena pre-sizing prevents the dangling-pointer / buffer-overrun bug."""
        # Without ``reserve_arena`` this would either segfault, corrupt the
        # key (producing 'U: xxx...' instead of 'k: xxx...'), or trigger
        # ryml's "not enough space in the given buffer" error.
        obj = {"k": "x" * 200_000}
        buf = io.StringIO()
        yaml_ryml.dump(obj, buf)
        assert yaml.safe_load(buf.getvalue()) == obj

    def test_control_characters_fall_back_to_pyyaml(self):
        """ryml does not escape control chars; we transparently use PyYAML."""
        obj = {"binary": "a\x01b\x02c"}
        buf = io.StringIO()
        yaml_ryml.dump(obj, buf)
        # PyYAML's loader rejects raw control chars; if the fallback engaged,
        # the output must round-trip cleanly.
        assert yaml.safe_load(buf.getvalue()) == obj


# ---------------------------------------------------------------------------
# Integration with CompilingFile.write_yaml
# ---------------------------------------------------------------------------
class TestWriteYamlDispatch:
    """``write_yaml`` should switch between PyYAML and ryml based on the flag."""

    @pytest.fixture(autouse=True)
    def _reset_cached(self):
        # Save & restore module-level state so tests don't leak into each other
        # or into the rest of the suite.
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
        # The revealer is built from ref_controller; make compile_obj a no-op
        # so we are isolated to YAML emission behaviour.
        with patch("kapitan.inputs.base.Revealer") as Revealer:
            revealer = Revealer.return_value
            revealer.compile_obj.side_effect = lambda o, **kw: o
            revealer.reveal_obj.side_effect = lambda o: o
            return CompilingFile(buf, ref_controller, target_name="t", indent=2)

    def test_default_uses_pyyaml(self):
        cached.args = Namespace()
        buf = io.StringIO()
        self._make_compiling_file(buf).write_yaml({"b": 1, "a": 2})
        # PyYAML's PrettyDumper indents nested sequences; ryml is irrelevant
        # here, but the marker we check is just that the output is valid and
        # keys are sorted.
        assert buf.getvalue() == "a: 2\nb: 1\n"

    def test_flag_routes_to_ryml(self):
        """When ``yaml_use_rapidyaml`` is set, ryml_dump is invoked."""
        cached.args = Namespace(yaml_use_rapidyaml=True)
        with patch("kapitan.inputs.base.ryml_dump") as ryml_dump:
            buf = io.StringIO()
            self._make_compiling_file(buf).write_yaml({"a": 1})
            assert ryml_dump.called, "ryml_dump was not invoked despite the flag"
            # Sanity-check the keyword args we expose.
            _, kwargs = ryml_dump.call_args
            assert kwargs["multi_doc"] is False
            assert "multiline_style" in kwargs
            assert "dump_null_as_empty" in kwargs

    def test_flag_off_keeps_pyyaml(self):
        cached.args = Namespace(yaml_use_rapidyaml=False)
        with patch("kapitan.inputs.base.ryml_dump") as ryml_dump:
            buf = io.StringIO()
            self._make_compiling_file(buf).write_yaml({"a": 1})
            assert not ryml_dump.called

    def test_pyyaml_and_ryml_paths_are_semantically_equivalent(self):
        """Both code paths must produce YAML that round-trips to the same dict."""
        sample = {
            "spec": {
                "replicas": 3,
                "containers": [{"name": "c1", "image": "nginx:1.21"}],
                "labels": {"env": "prod", "app": "x"},
            },
            "apiVersion": "apps/v1",
            "kind": "Deployment",
        }

        cached.args = Namespace()
        buf_py = io.StringIO()
        self._make_compiling_file(buf_py).write_yaml(sample)

        cached.args = Namespace(yaml_use_rapidyaml=True)
        buf_ryml = io.StringIO()
        self._make_compiling_file(buf_ryml).write_yaml(sample)

        assert yaml.safe_load(buf_py.getvalue()) == sample
        assert yaml.safe_load(buf_ryml.getvalue()) == sample


# ---------------------------------------------------------------------------
# CLI startup warning
# ---------------------------------------------------------------------------
class TestStartupWarning:
    """``trigger_compile`` warns once at startup when the flag is unusable."""

    def _run_trigger(self, args):
        from kapitan import cli

        with (
            patch("kapitan.cli.check_version"),
            patch("kapitan.cli.compile_targets"),
            patch("kapitan.cli.RefController", return_value=MagicMock()),
            patch("kapitan.cli.Revealer", return_value=MagicMock()),
        ):
            cli.trigger_compile(args)

    def _base_args(self, **overrides):
        # ``trigger_compile`` wraps ``compile_targets(inventory_path=args.inventory_path, ...)``
        # in a bare ``except`` that calls ``sys.exit(1)`` on *any* error. We
        # therefore have to populate every attribute that ``trigger_compile``
        # touches before reaching the mocked ``compile_targets``.
        ns = Namespace(
            ignore_version_check=True,
            search_paths=["."],
            refs_path="/tmp/r",
            embed_refs=False,
            inventory_path="./inventory",
            yaml_use_rapidyaml=False,
        )
        for k, v in overrides.items():
            setattr(ns, k, v)
        return ns

    def test_no_warning_when_flag_off(self, caplog):
        with caplog.at_level(logging.WARNING, logger="kapitan.cli"):
            self._run_trigger(self._base_args(yaml_use_rapidyaml=False))
        assert not any("rapidyaml" in r.message for r in caplog.records)

    def test_no_warning_when_flag_on_and_installed(self, caplog):
        with (
            patch.object(yaml_ryml, "HAS_RYML", True),
            caplog.at_level(logging.WARNING, logger="kapitan.cli"),
        ):
            self._run_trigger(self._base_args(yaml_use_rapidyaml=True))
        assert not any("rapidyaml" in r.message for r in caplog.records)

    def test_warning_logged_when_rapidyaml_missing(self, caplog):
        """Flag on + package missing => one-time WARNING at startup."""
        with (
            patch.object(yaml_ryml, "HAS_RYML", False),
            caplog.at_level(logging.WARNING, logger="kapitan.cli"),
        ):
            self._run_trigger(self._base_args(yaml_use_rapidyaml=True))

        matching = [r for r in caplog.records if "rapidyaml" in r.message]
        assert len(matching) == 1, f"expected exactly one warning, got {matching!r}"
        assert matching[0].levelno == logging.WARNING
        # The message should tell the user how to fix it.
        assert "pip install" in matching[0].message
