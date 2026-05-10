#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for deterministic compile output (FR-002).

Acceptance criteria verified here:
  - Running compile with -p 1 and -p 4 produces identical output trees.
  - All failing targets are reported in a single CompileError, not just the
    first one observed by the pool scheduler.
"""

import os
import tempfile
import unittest

import pytest
import yaml

from kapitan.cached import reset_cache
from kapitan.cli import build_parser
from kapitan.cli import main as kapitan
from kapitan.errors import CompileError
from kapitan.refs.base import RefController
from kapitan.targets import compile_targets
from kapitan.utils import directory_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Simple targets from test_resources that compile without external dependencies.
_SIMPLE_TARGETS = ["jinja2-postfix-strip", "jinja2-input-params", "toml-output"]


def _make_failing_target_yaml(target_name: str) -> dict:
    """Return an inventory dict for a target that will always fail at compile time."""
    return {
        "parameters": {
            "kapitan": {
                "vars": {"target": target_name},
                "compile": [
                    {
                        "name": "out",
                        "input_type": "copy",
                        # Path does not exist in any search_path → CompileError at compile time
                        "input_paths": ["__nonexistent_path_for_testing__"],
                        "output_path": "out",
                    }
                ],
            }
        }
    }


def _make_compile_args(extra_argv=()):
    """Return a parsed args Namespace suitable for passing to compile_targets."""
    argv = ["compile", "--ignore-version-check"] + list(extra_argv)
    return build_parser().parse_args(argv)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("isolated_test_resources")
class TestDeterministicCompile(unittest.TestCase):
    """Determinism contract for kapitan compile (FR-002)."""

    # ------------------------------------------------------------------
    # Criterion 3: -p 1 and -p 4 produce identical output trees
    # ------------------------------------------------------------------

    def test_p1_and_p4_output_identical(self):
        """Compile with -p 1 and -p 4 must produce byte-identical output trees."""
        with tempfile.TemporaryDirectory() as out1:
            with tempfile.TemporaryDirectory() as out2:
                reset_cache()
                kapitan(
                    "compile",
                    "-t",
                    *_SIMPLE_TARGETS,
                    "-p",
                    "1",
                    "--output-path",
                    out1,
                    "--ignore-version-check",
                )

                reset_cache()
                kapitan(
                    "compile",
                    "-t",
                    *_SIMPLE_TARGETS,
                    "-p",
                    "4",
                    "--output-path",
                    out2,
                    "--ignore-version-check",
                )

                hash_p1 = directory_hash(os.path.join(out1, "compiled"))
                hash_p4 = directory_hash(os.path.join(out2, "compiled"))

        self.assertEqual(
            hash_p1,
            hash_p4,
            "Compiled output tree must be byte-identical for -p 1 and -p 4",
        )

    # ------------------------------------------------------------------
    # Criterion 2: all failing targets are reported in a single error
    # ------------------------------------------------------------------

    def test_all_failing_targets_reported(self):
        """Every failing target must appear in the CompileError, not just the first one seen."""
        failing_names = ["broken-alpha", "broken-zeta"]

        for target_name in failing_names:
            target_file = os.path.join("inventory", "targets", f"{target_name}.yml")
            with open(target_file, "w") as fh:
                yaml.dump(_make_failing_target_yaml(target_name), fh)

        args = _make_compile_args(["-t", *failing_names, "-p", "2"])
        ref_controller = RefController(args.refs_path)
        search_paths = [os.path.abspath(p) for p in args.search_paths]

        with self.assertRaises(CompileError) as cm:
            compile_targets(
                inventory_path=args.inventory_path,
                search_paths=search_paths,
                ref_controller=ref_controller,
                args=args,
            )

        error_msg = str(cm.exception)
        for name in failing_names:
            self.assertIn(
                name,
                error_msg,
                f"Expected failing target '{name}' to appear in the CompileError "
                f"message, but it was missing.\nFull message:\n{error_msg}",
            )
