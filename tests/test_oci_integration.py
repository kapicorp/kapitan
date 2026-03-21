# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for the OCI dependency type against a real local registry."""

import tempfile
import unittest
from pathlib import Path

from kapitan.dependency_manager.base import fetch_oci_dependency
from kapitan.errors import OCIFetchingError
from kapitan.inventory.model.dependencies import KapitanDependencyOciConfig
from tests.oci_registry_server import OciRegistryServer


class OciDependencyIntegrationTest(unittest.TestCase):
    """End-to-end tests for fetch_oci_dependency() against a local registry:2 container."""

    @classmethod
    def setUpClass(cls):
        cls.registry = OciRegistryServer()

        # Build a small artifact tree on disk and push it once
        cls._artifact_dir = tempfile.mkdtemp()
        top = Path(cls._artifact_dir)

        # Root-level file
        (top / "config.yaml").write_text("key: value\n")

        # Sub-directory that tests subpath extraction
        subdir = top / "generators"
        subdir.mkdir()
        (subdir / "main.py").write_text("def main(): return {}\n")
        (subdir / "helpers.py").write_text("def noop(): pass\n")

        cls.reference = cls.registry.push_artifact(
            repository="test/kapitan-artifact",
            tag="v1",
            files=[str(top)],
        )

    @classmethod
    def tearDownClass(cls):
        cls.registry.close()
        import shutil

        shutil.rmtree(cls._artifact_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_dep(self, output_path, **kwargs):
        return KapitanDependencyOciConfig(
            type="oci",
            source=self.reference,
            output_path=output_path,
            insecure=True,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_full_pull_lands_files(self):
        """Pulling an artifact without subpath copies all files to output_path."""
        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir)
            fetch_oci_dependency((self.reference, [dep]), save_dir=save_dir)

            # The artifact dir itself gets pulled as a tar oras names it by directory
            artifact_name = Path(self._artifact_dir).name
            # Verify at least one known file is present somewhere under out_dir
            found = list(Path(out_dir).rglob("config.yaml"))
            self.assertTrue(found, "config.yaml not found in pulled artifact")

    def test_subpath_extracts_subdirectory(self):
        """Setting subpath copies only that subdirectory's contents into output_path."""
        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            # First do a full pull to warm the cache so we can inspect structure
            dep_full = self._make_dep(output_path=tempfile.mkdtemp())
            with tempfile.TemporaryDirectory() as probe_save:
                fetch_oci_dependency((self.reference, [dep_full]), save_dir=probe_save)
                # Find what oras actually named the extracted directory
                cache_key = (
                    __import__("hashlib")
                    .sha256(self.reference.encode())
                    .hexdigest()[:8]
                )
                cache_dir = Path(probe_save) / f"oci_{cache_key}"
                contents = list(cache_dir.iterdir()) if cache_dir.exists() else []

            # Determine the subpath from what was actually pulled
            # oras stores the directory under its basename
            artifact_basename = Path(self._artifact_dir).name
            subpath = f"{artifact_basename}/generators"

            dep = self._make_dep(output_path=out_dir, subpath=subpath)
            with tempfile.TemporaryDirectory() as save_dir:
                fetch_oci_dependency((self.reference, [dep]), save_dir=save_dir)

            pulled_files = {p.name for p in Path(out_dir).rglob("*") if p.is_file()}
            self.assertIn("main.py", pulled_files)
            self.assertIn("helpers.py", pulled_files)
            self.assertNotIn("config.yaml", pulled_files)

    def test_cache_hit_skips_second_pull(self):
        """A second fetch with the same save_dir reuses the cache without re-pulling."""
        from unittest.mock import patch

        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out1,
            tempfile.TemporaryDirectory() as out2,
        ):
            dep1 = self._make_dep(output_path=out1)
            # First pull real network hit
            fetch_oci_dependency((self.reference, [dep1]), save_dir=save_dir)

            dep2 = self._make_dep(output_path=out2)
            # Second pull cache should be hit; patch OrasClient to confirm no pull
            with patch(
                "kapitan.dependency_manager.base.oras.client.OrasClient"
            ) as MockClient:
                fetch_oci_dependency((self.reference, [dep2]), save_dir=save_dir)
                MockClient.return_value.pull.assert_not_called()

    def test_force_re_pulls(self):
        """force=True re-pulls even when cache exists."""

        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out1,
            tempfile.TemporaryDirectory() as out2,
        ):
            dep1 = self._make_dep(output_path=out1)
            fetch_oci_dependency((self.reference, [dep1]), save_dir=save_dir)

            dep2 = self._make_dep(output_path=out2)
            # force=True must clear cache and pull again
            fetch_oci_dependency(
                (self.reference, [dep2]), save_dir=save_dir, force=True
            )
            found = list(Path(out2).rglob("config.yaml"))
            self.assertTrue(found, "config.yaml not found after force re-pull")

    def test_invalid_subpath_raises_oci_fetching_error(self):
        """Requesting a subpath that doesn't exist in the artifact raises OCIFetchingError."""
        with (
            tempfile.TemporaryDirectory() as save_dir,
            tempfile.TemporaryDirectory() as out_dir,
        ):
            dep = self._make_dep(output_path=out_dir, subpath="does-not-exist")
            with self.assertRaises(OCIFetchingError):
                fetch_oci_dependency((self.reference, [dep]), save_dir=save_dir)
