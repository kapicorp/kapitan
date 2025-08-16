#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Refactored dependency manager tests using pytest fixtures for better isolation."""

import multiprocessing
import os
import sys
import tempfile
from shutil import rmtree

import pytest

from kapitan.cli import main
from kapitan.dependency_manager.base import (
    HelmSource,
    fetch_dependencies,
    fetch_git_dependency,
    fetch_git_source,
    fetch_helm_chart,
    fetch_http_source,
)
from kapitan.errors import HelmFetchingError
from kapitan.inventory.model import KapitanInventorySettings
from kapitan.inventory.model.dependencies import (
    KapitanDependencyGitConfig,
    KapitanDependencyHelmConfig,
)
from tests.test_helpers import CompileTestHelper


class TestHttpSources:
    """Test HTTP/HTTPS dependency sources."""

    def test_fetch_http_sources(self, temp_dir):
        """Tests fetching http[s] sources."""
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

        assert os.path.isfile(os.path.join(temp_dir, "1c3a08e6" + "jsonnet.jsonnet"))
        assert os.path.isfile(os.path.join(temp_dir, "aff45ec8" + "__init__.py"))


class TestGitSources:
    """Test Git dependency sources."""

    def test_fetch_git_sources(self, temp_dir):
        """Tests cloning git repo."""
        repo_dir = os.path.join(temp_dir, "7a8f3940kapitan.git")
        # TODO: also test git ssh urls
        git_source = "https://github.com/kapicorp/kapitan.git"
        fetch_git_source(git_source, repo_dir, item_type="Dependency")
        assert os.path.isfile(os.path.join(repo_dir, "README.md"))

    def test_clone_repo_subdir(self, temp_dir):
        """Tests cloning git repo and copy its' subdir."""
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir)

        source = "https://github.com/kapicorp/kapitan.git"
        dep = [
            KapitanDependencyGitConfig(
                **{
                    "type": "git",
                    "source": source,
                    "output_path": os.path.join(output_dir, "subdir"),
                    "ref": "master",
                    "subdir": "tests",
                }
            )
        ]
        fetch_git_dependency((source, dep), temp_dir, force=False)
        assert os.path.isdir(os.path.join(output_dir, "subdir"))


class TestHelmCharts:
    """Test Helm chart dependency fetching."""

    def test_fetch_helm_chart(self, temp_dir):
        """Tests fetching helm chart."""
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir)
        output_chart_dir = os.path.join(output_dir, "charts", "prometheus")
        chart_name = "prometheus"
        version = "11.3.0"
        repo = "https://github.com/BurdenBear/kube-charts-mirror/raw/master/docs/"
        dep = [
            KapitanDependencyHelmConfig(
                **{
                    "output_path": output_chart_dir,
                    "version": version,
                    "chart_name": chart_name,
                    "source": repo,
                }
            )
        ]
        fetch_helm_chart((HelmSource(repo, chart_name, version, None), dep), temp_dir, force=False)
        assert os.path.isdir(output_chart_dir)
        assert os.path.isfile(os.path.join(output_chart_dir, "Chart.yaml"))
        assert os.path.isdir(os.path.join(output_chart_dir, "charts", "kube-state-metrics"))

    def test_fetch_helm_chart_version_that_does_not_exist(self, temp_dir):
        """Test fetching helm chart version that does not exist."""
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir)
        output_chart_dir = os.path.join(output_dir, "charts", "prometheus")
        chart_name = "prometheus"
        version = "10.7.0"
        repo = "https://github.com/BurdenBear/kube-charts-mirror/raw/master/docs/"
        dep = [
            KapitanDependencyHelmConfig(
                **{
                    "output_path": output_chart_dir,
                    "version": version,
                    "chart_name": chart_name,
                    "source": repo,
                }
            )
        ]
        with pytest.raises(HelmFetchingError):
            fetch_helm_chart((HelmSource(repo, chart_name, version, None), dep), temp_dir, force=False)
        assert not os.path.isdir(output_chart_dir)
        assert not os.path.isfile(os.path.join(output_chart_dir, "Chart.yaml"))


class TestDependenciesParallel:
    """Test parallel dependency fetching."""

    def test_fetch_dependencies_unpack_parallel(self, temp_dir):
        """Test fetching and unpacking dependencies in parallel."""
        output_path = os.path.join(temp_dir, "output")
        save_dir = os.path.join(temp_dir, "save")
        os.makedirs(output_path)
        os.makedirs(save_dir)

        # use default parallelism of 4 for test
        with multiprocessing.Pool(4) as pool:
            dependencies = [
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

            inventory = KapitanInventorySettings(dependencies=dependencies)
            target_objs = [inventory]
            try:
                fetch_dependencies(output_path, target_objs, save_dir, False, pool)
                pool.close()
            except Exception as e:
                pool.terminate()
                raise e

        for obj in target_objs[0].dependencies:
            assert os.path.isdir(os.path.join(output_path, obj.output_path))
            assert os.path.isdir(os.path.join(save_dir, obj.output_path))


class TestCompileWithFetch:
    """Test compile command with fetch dependencies."""

    def test_compile_fetch(self, isolated_test_resources, temp_dir):
        """Test 'kapitan compile --fetch' command."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(
            [
                "kapitan",
                "compile",
                "--fetch",
                "--output-path",
                temp_dir,
                "-t",
                "nginx",
                "nginx-dev",
                "monitoring-dev",
            ]
        )

        assert os.path.isdir(os.path.join(temp_dir, "components", "tests"))
        assert os.path.isdir(os.path.join(temp_dir, "components", "acs-engine-autoscaler"))
        assert os.path.isdir(os.path.join(temp_dir, "components", "kapitan-repository"))
        assert os.path.isdir(os.path.join(temp_dir, "components", "source"))
        assert os.path.isdir(os.path.join(temp_dir, "charts", "prometheus"))
