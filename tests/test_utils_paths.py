#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for kapitan.utils.paths (FR-009)."""

import os

from kapitan.utils.paths import list_all_paths, normalise_join_path


class TestNormaliseJoinPath:
    def test_joins_paths(self):
        result = normalise_join_path("/base/dir", "subdir/file.txt")
        assert result == "/base/dir/subdir/file.txt"

    def test_normalises_double_slash(self):
        result = normalise_join_path("/base//dir", "file.txt")
        assert result == "/base/dir/file.txt"

    def test_resolves_dotdot(self):
        result = normalise_join_path("/base/a/b", "../../c")
        assert result == "/base/c"

    def test_relative_dirname(self):
        result = normalise_join_path("relative", "path/to/file")
        assert result == "relative/path/to/file"


class TestListAllPaths:
    def test_yields_all_files_and_dirs(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("hello")
        (tmp_path / "top.txt").write_text("world")

        results = list(list_all_paths(str(tmp_path)))
        # Should include subdir, subdir/file.txt, top.txt
        assert len(results) == 3

    def test_empty_directory(self, tmp_path):
        results = list(list_all_paths(str(tmp_path)))
        assert results == []

    def test_all_results_are_full_paths(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        for path in list_all_paths(str(tmp_path)):
            assert os.path.isabs(path)
