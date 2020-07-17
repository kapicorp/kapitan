#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import unittest
import tempfile
from shutil import rmtree
from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.dependency_manager.base import (
    fetch_git_source,
    fetch_http_source,
    fetch_git_dependency,
    fetch_helm_chart,
)


class DependencyManagerTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join(os.getcwd(), "tests", "test_resources"))

    def test_fetch_http_sources(self):
        "Tests fetching http[s] sources"
        temp_dir = tempfile.mkdtemp()
        http_sources = [
            (
                "https://raw.githubusercontent.com/deepmind/kapitan/master/examples/docker/components/jsonnet/jsonnet.jsonnet",
                "1c3a08e6jsonnet.jsonnet",
            ),
            (
                "https://raw.githubusercontent.com/deepmind/kapitan/master/examples/docker/components/kadet/__init__.py",
                "aff45ec8__init__.py",
            ),
        ]

        for source, path_hash in http_sources:
            fetch_http_source(source, os.path.join(temp_dir, path_hash), item_type="Dependency")

        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "1c3a08e6" + "jsonnet.jsonnet")))
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "aff45ec8" + "__init__.py")))
        rmtree(temp_dir)

    def test_fetch_git_sources(self):
        "Tests clonning git repo"
        temp_dir = tempfile.mkdtemp()
        repo_dir = os.path.join(temp_dir, "7a8f3940kapitan.git")
        # TODO: also test git ssh urls
        git_source = "https://github.com/deepmind/kapitan.git"
        fetch_git_source(git_source, repo_dir, item_type="Dependency")
        self.assertTrue(os.path.isfile(os.path.join(repo_dir, "README.md")))
        rmtree(temp_dir)

    def test_clone_repo_subdir(self):
        """
        Tests clonning git repo and copy its' subdir
        """
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        source = "https://github.com/deepmind/kapitan.git"
        dep = [{"output_path": os.path.join(output_dir, "subdir"), "ref": "master", "subdir": "tests",}]
        fetch_git_dependency((source, dep), temp_dir, force=False)
        self.assertTrue(os.path.isdir(os.path.join(output_dir, "subdir")))
        rmtree(temp_dir)
        rmtree(output_dir)

    def test_fetch_helm_chart(self):
        """
        Tests fetching helm chart
        """
        output_dir = tempfile.mkdtemp()
        output_chart_dir = os.path.join(output_dir, "charts", "prometheus")
        chart_name = "prometheus"
        version = "11.3.0"
        unique_chart_name = chart_name + "-" + version
        dep = [
            {
                "output_path": output_chart_dir,
                "version": version,
                "chart_name": chart_name,
                "source": "https://kubernetes-charts.storage.googleapis.com",
            }
        ]
        fetch_helm_chart((unique_chart_name, dep))
        self.assertTrue(os.path.isdir(output_chart_dir))
        self.assertTrue(os.path.isfile(os.path.join(output_chart_dir, "Chart.yaml")))
        self.assertTrue(os.path.isdir(os.path.join(output_chart_dir, "charts", "kube-state-metrics")))
        rmtree(output_dir)

    def test_fetch_helm_chart_version_that_does_not_exist(self):
        """
        Test fetching helm chart version that does not exist
        Runs $ kapitan compile --fetch --output-path temp -t nginx nginx-dev monitoring-dev
        """
        output_dir = tempfile.mkdtemp()
        output_chart_dir = os.path.join(output_dir, "charts", "prometheus")
        chart_name = "prometheus"
        version = "10.7.0"
        unique_chart_name = chart_name + "-" + version
        dep = [
            {
                "output_path": output_chart_dir,
                "version": version,
                "chart_name": chart_name,
                "source": "https://kubernetes-charts.storage.googleapis.com",
            }
        ]
        fetch_helm_chart((unique_chart_name, dep))
        self.assertFalse(os.path.isdir(output_chart_dir))
        self.assertFalse(os.path.isfile(os.path.join(output_chart_dir, "Chart.yaml")))
        rmtree(output_dir)

    def test_compile_fetch(self):
        temp = tempfile.mkdtemp()
        sys.argv = [
            "kapitan",
            "compile",
            "--fetch",
            "--output-path",
            temp,
            "-t",
            "nginx",
            "nginx-dev",
            "monitoring-dev",
        ]
        main()
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "tests")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "acs-engine-autoscaler")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "kapitan-repository")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "source")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "charts", "prometheus")))
        rmtree(temp)

    def tearDown(self):
        os.chdir("../../")
        reset_cache()
