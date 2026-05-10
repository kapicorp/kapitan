#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for kapitan.api — library-mode entry point."""

import os
import sys

import pytest

from kapitan.api import compile as kapitan_compile


class TestCompileAPINoSysArgv:
    """compile() must not consult sys.argv."""

    def test_compile_ignores_sys_argv(self, isolated_docker_inventory):
        original_argv = sys.argv[:]
        sys.argv = ["garbage", "--this-flag-does-not-exist"]
        try:
            kapitan_compile(inventory_path="./inventory", search_paths=[".", "lib"])
        finally:
            sys.argv = original_argv
        # reaching here means no argparse ran against sys.argv


class TestCompileAPIDockerExample:
    """Library-mode compile of the docker example."""

    def test_compile_without_process_restart(self, isolated_docker_inventory):
        """Compile docker example with no sys.argv / sys.exit involvement."""
        kapitan_compile(
            inventory_path="./inventory",
            search_paths=[".", "lib"],
            refs_path="./refs",
            output_path=".",
        )
        compiled = os.path.join(os.getcwd(), "compiled")
        assert os.path.isdir(compiled), "compiled/ directory must be created"

    def test_two_sequential_compiles_do_not_bleed(
        self, isolated_docker_inventory, temp_dir
    ):
        """Two back-to-back library-mode compiles must not share state."""

        # first compile into the docker inventory dir
        kapitan_compile(
            inventory_path="./inventory",
            search_paths=[".", "lib"],
            output_path=".",
        )
        first_compiled = os.path.join(os.getcwd(), "compiled")
        assert os.path.isdir(first_compiled)

        # second compile into a different output path
        second_out = os.path.join(temp_dir, "second_output")
        os.makedirs(second_out, exist_ok=True)
        kapitan_compile(
            inventory_path="./inventory",
            search_paths=[".", "lib"],
            output_path=second_out,
        )
        second_compiled = os.path.join(second_out, "compiled")
        assert os.path.isdir(second_compiled)


class TestCompileAPIErrors:
    """compile() raises exceptions instead of calling sys.exit."""

    def test_unknown_target_raises_exception(self, isolated_docker_inventory):
        with pytest.raises(Exception):
            kapitan_compile(
                inventory_path="./inventory",
                search_paths=[".", "lib"],
                targets=["nonexistent-target-xyz"],
            )

    def test_no_system_exit_on_error(self, isolated_docker_inventory):
        """compile() must never raise SystemExit."""
        with pytest.raises(Exception) as exc_info:
            kapitan_compile(
                inventory_path="./inventory",
                search_paths=[".", "lib"],
                targets=["nonexistent-target-xyz"],
            )
        assert not isinstance(
            exc_info.value, SystemExit
        ), "compile() raised SystemExit; it must raise a domain exception instead"


class TestArgparseRoundTrip:
    """Every documented compile flag must survive a parse_args() round trip."""

    @pytest.fixture(autouse=True)
    def _parser(self):
        from kapitan.cli import build_parser

        self.parser = build_parser()

    def _parse(self, *args):
        return self.parser.parse_args(["compile", *args])

    def test_targets(self):
        args = self._parse("--targets", "foo", "bar")
        assert args.targets == ["foo", "bar"]

    def test_labels(self):
        args = self._parse("--labels", "env=prod", "app=web")
        assert args.labels == ["env=prod", "app=web"]

    def test_output_path(self):
        args = self._parse("--output-path", "/tmp/out")
        assert args.output_path == "/tmp/out"

    def test_search_paths(self):
        args = self._parse("--search-paths", ".", "lib", "vendor")
        assert args.search_paths == [".", "lib", "vendor"]

    def test_refs_path(self):
        args = self._parse("--refs-path", "/tmp/refs")
        assert args.refs_path == "/tmp/refs"

    def test_inventory_path(self):
        args = self._parse("--inventory-path", "./my-inventory")
        assert args.inventory_path == "./my-inventory"

    def test_parallelism(self):
        args = self._parse("--parallelism", "4")
        assert args.parallelism == 4

    def test_indent(self):
        args = self._parse("--indent", "4")
        assert args.indent == 4

    def test_fetch(self):
        args = self._parse("--fetch")
        assert args.fetch is True

    def test_force_fetch(self):
        args = self._parse("--force-fetch")
        assert args.force_fetch is True

    def test_validate(self):
        args = self._parse("--validate")
        assert args.validate is True

    def test_reveal(self):
        args = self._parse("--reveal")
        assert args.reveal is True

    def test_no_reveal(self):
        args = self._parse("--no-reveal")
        assert args.reveal is False

    def test_embed_refs(self):
        args = self._parse("--embed-refs")
        assert args.embed_refs is True

    def test_prune(self):
        args = self._parse("--prune")
        assert args.prune is True

    def test_verbose(self):
        args = self._parse("--verbose")
        assert args.verbose is True

    def test_quiet(self):
        args = self._parse("--quiet")
        assert args.quiet is True

    def test_cache(self):
        args = self._parse("--cache")
        assert args.cache is True

    def test_use_go_jsonnet(self):
        args = self._parse("--use-go-jsonnet")
        assert args.use_go_jsonnet is True

    def test_ignore_version_check(self):
        args = self._parse("--ignore-version-check")
        assert args.ignore_version_check is True

    def test_yaml_multiline_string_style_folded(self):
        args = self._parse("--yaml-multiline-string-style", "folded")
        assert args.yaml_multiline_string_style == "folded"

    def test_yaml_dump_null_as_empty(self):
        args = self._parse("--yaml-dump-null-as-empty")
        assert args.yaml_dump_null_as_empty is True

    def test_schemas_path(self):
        args = self._parse("--schemas-path", "./my-schemas")
        assert args.schemas_path == "./my-schemas"

    def test_compose_target_name(self):
        args = self._parse("--compose-target-name")
        assert args.compose_target_name is True

    def test_jinja2_filters(self):
        args = self._parse("--jinja2-filters", "lib/my_filters.py")
        assert args.jinja2_filters == "lib/my_filters.py"

    def test_targets_and_labels_are_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            self._parse("--targets", "foo", "--labels", "env=prod")
