#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import unittest
import tempfile

from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.dependency_manager.base import (
    fetch_git_source,
    fetch_http_source,
    fetch_git_dependency,
    DEPENDENCY_OUTPUT_CONFIG,
)


class DependencyManagerTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join(os.getcwd(), "tests", "test_resources"))

    def test_fetch_http_sources(self):
        temp_dir = tempfile.mkdtemp()
        http_sources = [
            "https://raw.githubusercontent.com/deepmind/kapitan/master/examples/docker/components/jsonnet/jsonnet.jsonnet",
            "https://raw.githubusercontent.com/deepmind/kapitan/master/examples/docker/components/kadet/__init__.py",
        ]

        for source in http_sources:
            fetch_http_source(source, temp_dir)

        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "1c3a08e6" + "jsonnet.jsonnet")))
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "aff45ec8" + "__init__.py")))

    def test_fetch_git_sources(self):
        temp_dir = tempfile.mkdtemp()
        # TODO: also test git ssh urls
        git_source = "https://github.com/deepmind/kapitan.git"
        fetch_git_source(git_source, temp_dir)
        self.assertTrue(os.path.isdir(os.path.join(temp_dir, "kapitan.git", "kapitan")))

    def test_clone_repo_subdir(self):
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        source = "https://github.com/deepmind/kapitan.git"
        dep = [{"output_path": os.path.join(output_dir, "subdir"), "ref": "master", "subdir": "tests"}]
        fetch_git_dependency((source, dep), temp_dir)
        self.assertTrue(os.path.isdir(os.path.join(output_dir, "subdir")))

    def test_compile_fetch(self):
        temp = tempfile.mkdtemp()
        DEPENDENCY_OUTPUT_CONFIG["root_dir"] = temp
        sys.argv = [
            "kapitan",
            "compile",
            "--fetch",
            "--output-path",
            temp,
            "-t",
            "nginx",
            "nginx-dev",
            "-p",
            "4",
        ]
        main()
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "tests")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "acs-engine-autoscaler")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "kapitan-repository")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "source")))

    def tearDown(self):
        os.chdir("../../")
        reset_cache()
