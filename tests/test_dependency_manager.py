#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import io
import multiprocessing
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kapitan.cli import main as kapitan
from kapitan.dependency_manager.base import (
    HelmSource,
    fetch_dependencies,
    fetch_git_dependency,
    fetch_git_source,
    fetch_helm_chart,
    fetch_http_source,
    fetch_oci_dependency,
)
from kapitan.errors import HelmFetchingError, OCIFetchingError
from kapitan.inventory.model import KapitanInventorySettings
from kapitan.inventory.model.dependencies import (
    KapitanDependencyGitConfig,
    KapitanDependencyHelmConfig,
    KapitanDependencyOciConfig,
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
        kapitan(
            "compile",
            "--fetch",
            "--output-path",
            str(temp),
            "-t",
            "nginx",
            "monitoring-dev",
        )

        self.assertTrue((temp / "components" / "tests").is_dir())
        self.assertTrue((temp / "components" / "kapitan-repository").is_dir())
        self.assertTrue((temp / "charts" / "prometheus").is_dir())


class OciDependencyModelTest(unittest.TestCase):
    """Tests for the KapitanDependencyOciConfig Pydantic model."""

    def test_minimal_config(self):
        """A source and output_path are sufficient; all OCI-specific fields default to None/False."""
        dep = KapitanDependencyOciConfig(
            type="oci",
            source="ghcr.io/kapicorp/generators:1.2.0",
            output_path="components/generators",
        )
        self.assertEqual(dep.type, "oci")
        self.assertEqual(dep.source, "ghcr.io/kapicorp/generators:1.2.0")
        self.assertEqual(dep.output_path, "components/generators")
        self.assertIsNone(dep.subpath)
        self.assertIsNone(dep.media_type)
        self.assertFalse(dep.insecure)
        self.assertFalse(dep.force_fetch)

    def test_digest_pinned_source(self):
        """source accepts a tag+digest reference."""
        dep = KapitanDependencyOciConfig(
            type="oci",
            source="ghcr.io/kapicorp/generators:1.2.0@sha256:abc123",
            output_path="components/generators",
        )
        self.assertIn("@sha256:", dep.source)

    def test_full_config(self):
        """All optional fields are accepted."""
        dep = KapitanDependencyOciConfig(
            type="oci",
            source="ghcr.io/kapicorp/generators:1.2.0",
            output_path="components/generators",
            subpath="kubernetes/",
            media_type="application/vnd.kapitan.generator.layer.v1.tar+gzip",
            insecure=True,
            force_fetch=True,
        )
        self.assertEqual(dep.subpath, "kubernetes/")
        self.assertEqual(
            dep.media_type, "application/vnd.kapitan.generator.layer.v1.tar+gzip"
        )
        self.assertTrue(dep.insecure)
        self.assertTrue(dep.force_fetch)

    def test_oci_included_in_dependency_union(self):
        """KapitanInventorySettings accepts type: oci in its dependencies list."""
        settings = KapitanInventorySettings(
            dependencies=[
                {
                    "type": "oci",
                    "source": "ghcr.io/kapicorp/generators:1.2.0",
                    "output_path": "components/generators",
                }
            ]
        )
        dep = settings.dependencies[0]
        self.assertIsInstance(dep, KapitanDependencyOciConfig)


class OciFetchDependencyTest(unittest.TestCase):
    """Tests for fetch_oci_dependency() — all network calls are mocked."""

    def _make_dep(
        self,
        source="ghcr.io/kapicorp/generators:1.2.0",
        output_path=None,
        subpath=None,
        media_type=None,
        insecure=False,
    ):
        return KapitanDependencyOciConfig(
            type="oci",
            source=source,
            output_path=output_path or tempfile.mkdtemp(),
            subpath=subpath,
            media_type=media_type,
            insecure=insecure,
        )

    def _seed_cache(self, target_dir: Path):
        """Write a stub generator into target_dir to simulate a cached pull."""
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "__init__.py").write_text("def main(): return {}")

    @patch("kapitan.dependency_manager.base.oras.client.OrasClient")
    def test_successful_pull(self, MockClient):
        """Files are pulled from the registry and copied to output_path."""
        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir)

            # Simulate oras writing a file into target_dir during pull
            def fake_pull(target, outdir, media_types):
                Path(outdir).mkdir(parents=True, exist_ok=True)
                (Path(outdir) / "__init__.py").write_text("def main(): return {}")

            MockClient.return_value.pull.side_effect = fake_pull

            fetch_oci_dependency((dep.source, [dep]), save_dir=save_dir, force=False)

            MockClient.return_value.pull.assert_called_once()
            self.assertTrue((Path(out_dir) / "__init__.py").is_file())

    @patch("kapitan.dependency_manager.base.oras.client.OrasClient")
    def test_cache_hit_skips_pull(self, MockClient):
        """A second fetch with the same source reuses the cached directory."""
        import hashlib

        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir)

            # Pre-populate the cache directory for this source
            cache_key = hashlib.sha256(dep.source.encode()).hexdigest()[:8]
            cached = Path(save_dir) / f"oci_{cache_key}"
            self._seed_cache(cached)

            fetch_oci_dependency((dep.source, [dep]), save_dir=save_dir, force=False)

            MockClient.return_value.pull.assert_not_called()

    @patch("kapitan.dependency_manager.base.oras.client.OrasClient")
    def test_force_bypasses_cache(self, MockClient):
        """force=True re-pulls even when a cache entry already exists."""
        import hashlib

        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir)

            # Pre-populate the cache
            cache_key = hashlib.sha256(dep.source.encode()).hexdigest()[:8]
            cached = Path(save_dir) / f"oci_{cache_key}"
            self._seed_cache(cached)

            def fake_pull(target, outdir, media_types):
                Path(outdir).mkdir(parents=True, exist_ok=True)
                (Path(outdir) / "__init__.py").write_text("def main(): return {}")

            MockClient.return_value.pull.side_effect = fake_pull

            fetch_oci_dependency((dep.source, [dep]), save_dir=save_dir, force=True)

            MockClient.return_value.pull.assert_called_once()

    @patch("kapitan.dependency_manager.base.oras.client.OrasClient")
    def test_subpath_is_extracted(self, MockClient):
        """When subpath is set, only that subdirectory is copied to output_path."""
        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir, subpath="kubernetes")

            def fake_pull(target, outdir, media_types):
                subdir = Path(outdir) / "kubernetes"
                subdir.mkdir(parents=True, exist_ok=True)
                (subdir / "__init__.py").write_text("def main(): return {}")
                # A sibling directory that should NOT appear in output_path
                other = Path(outdir) / "terraform"
                other.mkdir(parents=True, exist_ok=True)

            MockClient.return_value.pull.side_effect = fake_pull

            fetch_oci_dependency((dep.source, [dep]), save_dir=save_dir, force=False)

            self.assertTrue((Path(out_dir) / "__init__.py").is_file())
            self.assertFalse((Path(out_dir) / "terraform").exists())

    @patch("kapitan.dependency_manager.base.oras.client.OrasClient")
    def test_insecure_flag_forwarded(self, MockClient):
        """insecure=True is passed through to OrasClient."""
        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir, insecure=True)

            def fake_pull(target, outdir, media_types):
                Path(outdir).mkdir(parents=True, exist_ok=True)

            MockClient.return_value.pull.side_effect = fake_pull

            fetch_oci_dependency((dep.source, [dep]), save_dir=save_dir, force=False)

            MockClient.assert_called_once_with(insecure=True)

    @patch("kapitan.dependency_manager.base.oras.client.OrasClient")
    def test_pull_failure_raises_oci_fetching_error(self, MockClient):
        """A registry error is wrapped in OCIFetchingError."""
        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir)
            MockClient.return_value.pull.side_effect = Exception("connection refused")

            with self.assertRaises(OCIFetchingError):
                fetch_oci_dependency(
                    (dep.source, [dep]), save_dir=save_dir, force=False
                )

    @patch("kapitan.dependency_manager.base.oras.client.OrasClient")
    def test_multiple_deps_same_source(self, MockClient):
        """Two deps with the same source share a single pull (the dep_mapping pattern)."""
        with tempfile.TemporaryDirectory() as save_dir:
            out1 = tempfile.mkdtemp()
            out2 = tempfile.mkdtemp()
            source = "ghcr.io/kapicorp/generators:1.2.0"
            deps = [
                self._make_dep(source=source, output_path=out1),
                self._make_dep(source=source, output_path=out2),
            ]

            def fake_pull(target, outdir, media_types):
                Path(outdir).mkdir(parents=True, exist_ok=True)
                (Path(outdir) / "__init__.py").write_text("def main(): return {}")

            MockClient.return_value.pull.side_effect = fake_pull

            fetch_oci_dependency((source, deps), save_dir=save_dir, force=False)

            # Pull happens once; both output paths are populated
            MockClient.return_value.pull.assert_called_once()
            self.assertTrue((Path(out1) / "__init__.py").is_file())
            self.assertTrue((Path(out2) / "__init__.py").is_file())


class OciDependencyWiringTest(unittest.TestCase):
    """Tests that fetch_dependencies() dispatches OCI deps to fetch_oci_dependency()."""

    @patch("kapitan.dependency_manager.base.fetch_oci_dependency")
    def test_oci_deps_are_dispatched(self, mock_fetch_oci):
        """fetch_dependencies routes type:oci items to fetch_oci_dependency."""
        # Use ThreadPool instead of multiprocessing.Pool: threads share memory so
        # MagicMock objects don't need to be pickled across process boundaries.
        from multiprocessing.pool import ThreadPool

        with (
            tempfile.TemporaryDirectory() as output_path,
            tempfile.TemporaryDirectory() as save_dir,
        ):
            settings = KapitanInventorySettings(
                dependencies=[
                    {
                        "type": "oci",
                        "source": "ghcr.io/kapicorp/generators:1.2.0",
                        "output_path": "components/generators",
                    }
                ]
            )
            with ThreadPool(1) as pool:
                fetch_dependencies(
                    output_path, [settings], save_dir, force=False, pool=pool
                )

            mock_fetch_oci.assert_called_once()
