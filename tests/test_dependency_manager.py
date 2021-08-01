#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import multiprocessing
import os
import sys
import tempfile
import unittest
from shutil import rmtree

from kapitan.errors import HelmFetchingError
from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.dependency_manager.base import (
    fetch_git_source,
    fetch_http_source,
    fetch_git_dependency,
    fetch_helm_chart,
    fetch_dependencies,
    HelmSource,
)


class DependencyManagerTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join(os.getcwd(), "tests", "test_resources"))

    def test_fetch_http_sources(self):
        "Tests fetching http[s] sources"
        temp_dir = tempfile.mkdtemp()
        http_sources = [
            (
                "https://raw.githubusercontent.com/kapicorp/kapitan/master/examples/docker/components/jsonnet/jsonnet.jsonnet",
                "1c3a08e6jsonnet.jsonnet",
            ),
            (
                "https://raw.githubusercontent.com/kapicorp/kapitan/master/examples/docker/components/kadet/__init__.py",
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
        git_source = "https://github.com/kapicorp/kapitan.git"
        fetch_git_source(git_source, repo_dir, item_type="Dependency")
        self.assertTrue(os.path.isfile(os.path.join(repo_dir, "README.md")))
        rmtree(temp_dir)

    def test_clone_repo_subdir(self):
        """
        Tests clonning git repo and copy its' subdir
        """
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        source = "https://github.com/kapicorp/kapitan.git"
        dep = [
            {
                "output_path": os.path.join(output_dir, "subdir"),
                "ref": "master",
                "subdir": "tests",
            }
        ]
        fetch_git_dependency((source, dep), temp_dir, force=False)
        self.assertTrue(os.path.isdir(os.path.join(output_dir, "subdir")))
        rmtree(temp_dir)
        rmtree(output_dir)

    def test_fetch_helm_chart(self):
        """
        Tests fetching helm chart
        """
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        output_chart_dir = os.path.join(output_dir, "charts", "prometheus")
        chart_name = "prometheus"
        version = "11.3.0"
        repo = "https://github.com/BurdenBear/kube-charts-mirror/raw/master/docs/"
        dep = [
            {
                "output_path": output_chart_dir,
                "version": version,
                "chart_name": chart_name,
                "source": repo,
            }
        ]
        fetch_helm_chart((HelmSource(repo, chart_name, version, None), dep), temp_dir, force=False)
        self.assertTrue(os.path.isdir(output_chart_dir))
        self.assertTrue(os.path.isfile(os.path.join(output_chart_dir, "Chart.yaml")))
        self.assertTrue(os.path.isdir(os.path.join(output_chart_dir, "charts", "kube-state-metrics")))
        rmtree(temp_dir)
        rmtree(output_dir)

    def test_fetch_helm_chart_version_that_does_not_exist(self):
        """
        Test fetching helm chart version that does not exist
        """
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        output_chart_dir = os.path.join(output_dir, "charts", "prometheus")
        chart_name = "prometheus"
        version = "10.7.0"
        repo = "https://github.com/BurdenBear/kube-charts-mirror/raw/master/docs/"
        dep = [
            {
                "output_path": output_chart_dir,
                "version": version,
                "chart_name": chart_name,
                "source": repo,
            }
        ]
        with self.assertRaises(HelmFetchingError):
            fetch_helm_chart((HelmSource(repo, chart_name, version, None), dep), temp_dir, force=False)
        self.assertFalse(os.path.isdir(output_chart_dir))
        self.assertFalse(os.path.isfile(os.path.join(output_chart_dir, "Chart.yaml")))
        rmtree(temp_dir)
        rmtree(output_dir)

    def test_fetch_dependencies_unpack_parallel(self):
        output_path = tempfile.mkdtemp()
        save_dir = tempfile.mkdtemp()
        # use default parallelism of 4 for test
        pool = multiprocessing.Pool(4)
        target_objs = [
            {
                "dependencies": [
                    {
                        "type": "https",
                        "source": "https://github.com/BurdenBear/kube-charts-mirror/raw/master/docs/nfs-client-provisioner-1.2.8.tgz",
                        "output_path": "nfs-client-provisioner",
                        "unpack": True,
                    },
                    {
                        "type": "https",
                        "source": "https://github.com/BurdenBear/kube-charts-mirror/raw/master/docs/prometheus-pushgateway-1.2.13.tgz",
                        "output_path": "prometheus-pushgateway",
                        "unpack": True,
                    },
                ]
            }
        ]
        try:
            fetch_dependencies(output_path, target_objs, save_dir, False, pool)
            pool.close()
        except Exception as e:
            pool.terminate()
            raise e
        finally:
            pool.join()

        for obj in target_objs[0]["dependencies"]:
            self.assertTrue(os.path.isdir(os.path.join(output_path, obj["output_path"])))
            self.assertTrue(os.path.isdir(os.path.join(save_dir, obj["output_path"])))
        rmtree(output_path)
        rmtree(save_dir)

    def test_compile_fetch(self):
        "Runs $ kapitan compile --fetch --output-path temp -t nginx nginx-dev monitoring-dev"
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
