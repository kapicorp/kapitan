#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import io
import multiprocessing
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

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


def _http_sources_dir() -> Path:
    return Path(__file__).parent / "test_resources" / "http_sources"


def _read_http_source(filename: str) -> bytes:
    return (_http_sources_dir() / filename).read_bytes()


def _expect_http_file(httpserver, path: str, content, content_type: str) -> None:
    httpserver.expect_request(path).respond_with_data(
        content, content_type=content_type
    )


def _expect_index_yaml(
    httpserver, base_path: str, chart_name: str, version: str, chart_filename: str
) -> None:
    index_yaml = f"""
    apiVersion: v1
    entries:
      {chart_name}:
      - name: {chart_name}
        version: {version}
        urls:
        - {chart_filename}
    """

    path = f"{base_path.rstrip('/')}/index.yaml"
    _expect_http_file(httpserver, path, index_yaml, content_type="text/yaml")


def _expect_chart_archive(
    httpserver, base_path: str, chart_filename: str, content: bytes
) -> None:
    path = f"{base_path.rstrip('/')}/{chart_filename}"
    _expect_http_file(httpserver, path, content, content_type="application/gzip")


def _make_zip_bytes(files: dict[str, str]):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, payload in files.items():
            zf.writestr(filename, payload)
    return zip_buffer.getvalue()


@pytest.mark.usefixtures("isolated_test_resources", "local_http_server")
class DependencyManagerTest(unittest.TestCase):
    def test_fetch_http_sources(self):
        "Tests fetching http[s] sources"
        temp_dir = Path(self.isolated_test_resources)
        http_sources = [
            ("/jsonnet.jsonnet", "4897ec6.jsonnet.jsonnet"),
            ("/__init__.py", "4897ec6.__init__.py"),
        ]

        for path, source_file in http_sources:
            content = _read_http_source(source_file)
            _expect_http_file(self.httpserver, path, content, content_type="text/plain")

            output_path = temp_dir / path.lstrip("/")
            fetch_http_source(
                self.httpserver.url_for(path), str(output_path), item_type="Dependency"
            )

            self.assertTrue(output_path.is_file())
            self.assertEqual(output_path.read_bytes(), content)

    @pytest.mark.usefixtures("seeded_git_repo")
    def test_fetch_git_sources(self):
        "Tests cloning git repo"
        temp_dir = Path(self.isolated_test_resources)
        repo_dir = temp_dir / "repo.git"

        # TODO: also test git ssh urls
        fetch_git_source(
            str(self.seeded_git_repo), str(repo_dir), item_type="Dependency"
        )

        readme = repo_dir / "README.md"
        self.assertTrue(readme.is_file())

    @pytest.mark.usefixtures("seeded_git_repo")
    def test_clone_repo_subdir(self):
        """
        Tests cloning git repo and copy its' subdir
        """
        temp_dir = Path(self.isolated_test_resources)
        output_dir = Path(tempfile.mkdtemp())
        subdir = output_dir / "subdir"

        source = str(self.seeded_git_repo)
        dep = [
            KapitanDependencyGitConfig(
                type="git",
                source=source,
                output_path=str(subdir),
                ref="master",
                subdir="tests",
            )
        ]
        fetch_git_dependency((source, dep), str(temp_dir), force=False)
        self.assertTrue(subdir.is_dir())

    def test_fetch_helm_chart_http(self):
        """
        Tests fetching helm chart
        """
        temp_dir = Path(self.isolated_test_resources)
        output_dir = Path(tempfile.mkdtemp())
        output_chart_dir = output_dir / "charts" / "prometheus"

        chart_name = "prometheus"
        version = "11.3.0"
        chart_filename = f"{chart_name}-{version}.tgz"

        chart_content = _read_http_source(f"e452e07.{chart_filename}")
        _expect_index_yaml(self.httpserver, "/", chart_name, version, chart_filename)
        _expect_chart_archive(self.httpserver, "/", chart_filename, chart_content)
        repo = self.httpserver.url_for("/")
        dep = [
            KapitanDependencyHelmConfig(
                output_path=str(output_chart_dir),
                version=version,
                chart_name=chart_name,
                source=repo,
            )
        ]
        fetch_helm_chart(
            (HelmSource(repo, chart_name, version, None), dep),
            str(temp_dir),
            force=False,
        )
        self.assertTrue(output_chart_dir.is_dir())
        self.assertTrue((output_chart_dir / "Chart.yaml").is_file())
        self.assertTrue((output_chart_dir / "charts" / "kube-state-metrics").is_dir())

    def test_fetch_helm_chart_oci(self):
        """
        Tests fetching helm chart
        """
        temp_dir = Path(self.isolated_test_resources)
        output_dir = Path(tempfile.mkdtemp())
        output_chart_dir = output_dir / "charts" / "kserve-crd"

        chart_name = "kserve-crd"
        version = "v0.16.0"
        repo = "oci://ghcr.io/kserve/charts/kserve-crd"
        dep = [
            KapitanDependencyHelmConfig(
                output_path=str(output_chart_dir),
                version=version,
                chart_name=chart_name,
                source=repo,
            )
        ]
        fetch_helm_chart(
            (HelmSource(repo, chart_name, version, None), dep),
            str(temp_dir),
            force=False,
        )
        self.assertTrue(output_chart_dir.is_dir())
        self.assertTrue((output_chart_dir / "Chart.yaml").is_file())

    def test_fetch_helm_chart_version_that_does_not_exist(self):
        """
        Test fetching helm chart version that does not exist
        """
        temp_dir = Path(self.isolated_test_resources)
        output_dir = Path(tempfile.mkdtemp())
        output_chart_dir = output_dir / "charts" / "prometheus"

        chart_name = "prometheus"
        version = "10.7.0"
        repo = self.httpserver.url_for("/charts")
        self.httpserver.expect_request("/charts/index.yaml").respond_with_data(
            "not found", status=404, content_type="text/plain"
        )
        dep = [
            KapitanDependencyHelmConfig(
                output_path=str(output_chart_dir),
                version=version,
                chart_name=chart_name,
                source=repo,
            )
        ]
        with self.assertRaises(HelmFetchingError):
            fetch_helm_chart(
                (HelmSource(repo, chart_name, version, None), dep),
                str(temp_dir),
                force=False,
            )
        self.assertFalse(output_chart_dir.is_dir())
        self.assertFalse((output_chart_dir / "Chart.yaml").is_file())

    def test_fetch_dependencies_unpack_parallel(self):
        output_path = Path(tempfile.mkdtemp())
        save_dir = Path(self.isolated_test_resources)
        # use default parallelism of 4 for test
        with multiprocessing.Pool(4) as pool:
            http_sources = [
                (
                    "/nfs-client-provisioner-1.2.8.tgz",
                    "e452e07.nfs-client-provisioner-1.2.8.tgz",
                    "nfs-client-provisioner",
                ),
                (
                    "/prometheus-pushgateway-1.2.13.tgz",
                    "e452e07.prometheus-pushgateway-1.2.13.tgz",
                    "prometheus-pushgateway",
                ),
            ]
            dependencies = []

            for path, source_file, output_dir in http_sources:
                content = _read_http_source(source_file)
                _expect_http_file(
                    self.httpserver, path, content, content_type="application/gzip"
                )

                dependencies.append(
                    {
                        "type": "http",
                        "source": self.httpserver.url_for(path),
                        "output_path": output_dir,
                        "unpack": True,
                    }
                )

            inventory = KapitanInventorySettings(dependencies=dependencies)
            target_objs = [inventory]
            try:
                fetch_dependencies(
                    str(output_path), target_objs, str(save_dir), False, pool
                )
                pool.close()
            except Exception as e:
                pool.terminate()
                raise e

        for obj in target_objs[0].dependencies:
            for path in (output_path, save_dir):
                dir_path = Path(path) / obj.output_path
                self.assertTrue(dir_path.is_dir())

    @pytest.mark.usefixtures("seeded_git_repo")
    def test_compile_fetch(self):
        """
        Runs $ kapitan compile --fetch --output-path temp -t nginx monitoring-dev
        """
        temp_dir = Path(self.isolated_test_resources)

        chart_name = "prometheus"
        version = "11.3.0"
        chart_filename = f"{chart_name}-{version}.tgz"

        chart_content = _read_http_source(f"e452e07.{chart_filename}")

        _expect_index_yaml(self.httpserver, "/", chart_name, version, chart_filename)
        _expect_chart_archive(self.httpserver, "/", chart_filename, chart_content)

        zip_content = _make_zip_bytes({"kapitan-master/README.md": "test\n"})
        _expect_http_file(
            self.httpserver, "/master.zip", zip_content, content_type="application/zip"
        )

        nginx_target_path = temp_dir / "inventory" / "targets" / "nginx.yml"
        nginx_target = nginx_target_path.read_text(encoding="utf-8")

        nginx_target = nginx_target.replace(
            "source: https://github.com/kapicorp/kapitan.git",
            f"source: {self.seeded_git_repo}",
        )
        nginx_target = nginx_target.replace(
            "source: https://github.com/kapicorp/kapitan/archive/master.zip",
            f"source: {self.httpserver.url_for('/master.zip')}",
        )

        nginx_target_path.write_text(nginx_target, encoding="utf-8")

        monitoring_class_path = (
            temp_dir / "inventory" / "classes" / "component" / "monitoring.yml"
        )
        monitoring_class = monitoring_class_path.read_text(encoding="utf-8")

        repo_url = self.httpserver.url_for("/")

        monitoring_class = monitoring_class.replace(
            "source: https://github.com/BurdenBear/kube-charts-mirror/raw/master/docs/",
            f"source: {repo_url}",
        )

        monitoring_class_path.write_text(monitoring_class, encoding="utf-8")

        temp = Path(tempfile.mkdtemp())
        sys.argv = [
            "kapitan",
            "compile",
            "--fetch",
            "--output-path",
            str(temp),
            "-t",
            "nginx",
            "monitoring-dev",
        ]
        main()

        self.assertTrue((temp / "components" / "tests").is_dir())
        self.assertTrue((temp / "components" / "kapitan-repository").is_dir())
        self.assertTrue((temp / "charts" / "prometheus").is_dir())
