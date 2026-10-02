#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"helm input tests"

import io
import os
import tempfile
import unittest

import pytest
import yaml

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan
from kapitan.inputs.helm import Helm, HelmChart, write_helm_values_file
from kapitan.inputs.kadet import BaseObj
from kapitan.inventory.model.input_types import KapitanInputTypeHelmConfig


TEST_PWD = os.getcwd()


class HelmInputTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join("tests", "test_resources"))

    def test_render_chart(self):
        temp_dir = tempfile.mkdtemp()
        chart_path = "charts/acs-engine-autoscaler"
        helm_params = {"name": "acs-engine-autoscaler"}
        helm_config = KapitanInputTypeHelmConfig(
            input_paths=[chart_path], helm_params=helm_params, output_path=temp_dir
        )
        helm = Helm(None, None, None, None, None)
        _, error_message = helm.render_chart(
            chart_path,
            temp_dir,
            helm_config.helm_path,
            helm_config.helm_params,
            None,
            None,
        )
        self.assertFalse(error_message)
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp_dir, "acs-engine-autoscaler", "templates", "secrets.yaml"
                )
            )
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp_dir, "acs-engine-autoscaler", "templates", "deployment.yaml"
                )
            )
        )

    def test_error_invalid_chart_dir(self):
        chart_path = "./non-existent"
        temp_dir = tempfile.mkdtemp()
        helm_params = {"name": "mychart"}
        helm_config = KapitanInputTypeHelmConfig(
            input_paths=[chart_path], output_path=temp_dir, helm_params=helm_params
        )
        helm = Helm(None, None, None, None, None)
        _, error_message = helm.render_chart(
            chart_path,
            temp_dir,
            helm_config.helm_path,
            helm_config.helm_params,
            None,
            None,
        )
        self.assertTrue("path" in error_message and "not found" in error_message)

    def test_compile_chart(self):
        temp = tempfile.mkdtemp()
        kapitan("compile", "--output-path", temp, "-t", "acs-engine-autoscaler")
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp,
                    "compiled",
                    "acs-engine-autoscaler",
                    "acs-engine-autoscaler",
                    "templates",
                    "secrets.yaml",
                )
            )
        )

    def test_compile_subcharts(self):
        temp = tempfile.mkdtemp()
        kapitan("compile", "--output-path", temp, "-t", "istio")
        self.assertTrue(
            os.path.isdir(os.path.join(temp, "compiled", "istio", "istio", "charts"))
        )
        self.assertTrue(
            os.path.isdir(os.path.join(temp, "compiled", "istio", "istio", "templates"))
        )

    def test_compile_multiple_targets(self):
        temp = tempfile.mkdtemp()
        kapitan(
            "compile",
            "--output-path",
            temp,
            "-t",
            "acs-engine-autoscaler",
            "nginx-ingress",
            "-p",
            "2",
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp,
                    "compiled",
                    "acs-engine-autoscaler",
                    "acs-engine-autoscaler",
                    "templates",
                    "secrets.yaml",
                )
            )
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp,
                    "compiled",
                    "nginx-ingress",
                    "nginx-ingress",
                    "templates",
                    "clusterrolebinding.yaml",
                )
            )
        )

    def test_compile_multiple_charts_per_target(self):
        temp = tempfile.mkdtemp()
        kapitan("compile", "--output-path", temp, "-t", "nginx-istio")
        self.assertTrue(
            os.path.isdir(
                os.path.join(temp, "compiled", "nginx-istio", "istio", "templates")
            )
        )
        self.assertTrue(
            os.path.isdir(
                os.path.join(
                    temp, "compiled", "nginx-istio", "nginx-ingress", "templates"
                )
            )
        )

    def test_compile_with_helm_values(self):
        temp = tempfile.mkdtemp()
        kapitan("compile", "--output-path", temp, "-t", "nginx-ingress")
        controller_deployment_file = os.path.join(
            temp,
            "compiled",
            "nginx-ingress",
            "nginx-ingress",
            "templates",
            "controller-deployment.yaml",
        )
        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file) as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest["metadata"]["name"]
            self.assertEqual("release-name-nginx-ingress-my-controller", name)

    def test_compile_with_helm_values_files(self):
        temp = tempfile.mkdtemp()
        kapitan(
            "compile",
            "--output-path",
            temp,
            "-t",
            "monitoring-dev",
            "monitoring-prd",
        )
        dev_server_deployment_file = os.path.join(
            temp,
            "compiled",
            "monitoring-dev",
            "prometheus",
            "templates",
            "server-deployment.yaml",
        )
        prd_server_deployment_file = os.path.join(
            temp,
            "compiled",
            "monitoring-prd",
            "prometheus",
            "templates",
            "server-deployment.yaml",
        )

        self.assertTrue(os.path.isfile(dev_server_deployment_file))
        with open(dev_server_deployment_file) as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest["metadata"]["name"]
            self.assertEqual(name, "prometheus-dev-server")

        self.assertTrue(os.path.isfile(prd_server_deployment_file))
        with open(prd_server_deployment_file) as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest["metadata"]["name"]
            self.assertEqual(name, "prometheus-prd-server")

    def test_compile_with_helm_params(self):
        temp = tempfile.mkdtemp()
        argv = [
            "compile",
            "--output-path",
            temp,
            "-t",
            "nginx-ingress-helm-params",
        ]
        with open("inventory/targets/nginx-ingress-helm-params.yml") as fp:
            manifest = yaml.safe_load(fp.read())
            helm_params = manifest["parameters"]["kapitan"]["compile"][0]["helm_params"]
            release_name = helm_params["name"]
            namespace = helm_params["namespace"]

        kapitan(*argv)
        controller_deployment_file = os.path.join(
            temp,
            "compiled",
            "nginx-ingress-helm-params",
            "nginx-ingress",
            "templates",
            "controller-deployment.yaml",
        )

        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file) as fp:
            manifest = yaml.safe_load(fp.read())
            container = manifest["spec"]["template"]["spec"]["containers"][0]
            property = container["args"][4]
            self.assertEqual(
                property,
                "--configmap={}/{}".format(
                    namespace, release_name + "-nginx-ingress-my-controller"
                ),
            )

    @pytest.mark.usefixtures("setup_gpg_key")
    def test_compile_with_refs(self):
        temp = tempfile.mkdtemp()
        kapitan("compile", "--output-path", temp, "-t", "nginx-ingress", "--reveal")
        controller_deployment_file = os.path.join(
            temp,
            "compiled",
            "nginx-ingress",
            "nginx-ingress",
            "templates",
            "controller-deployment.yaml",
        )
        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file) as fp:
            manifest = yaml.safe_load(fp.read())
            args = next(
                iter(
                    c["args"]
                    for c in manifest["spec"]["template"]["spec"]["containers"]
                    if c["name"] == "nginx-ingress-my-controller"
                )
            )
            self.assertIn("--election-id=super_secret_ID", args)

    def test_compile_kadet_helm_chart(self):
        # Render chart
        chart = HelmChart(chart_dir="charts/prometheus/")

        # Number of keys must be greater than 0
        self.assertTrue(len(chart.root.keys()) > 0)
        # All values must be BaseObj
        for resource_name in chart.root:
            self.assertIsInstance(chart.root[resource_name], BaseObj)

    def test_numeric_string_values_preserved(self):
        """
        Test that numeric-looking strings with leading zeros are preserved.

        This tests the bug reported in https://github.com/kapicorp/kapitan/issues/1370
        where string values like "03190301" are converted to scientific notation
        (3.190301e+06) because they pass through YAML without proper quoting.
        """
        temp = tempfile.mkdtemp()
        kapitan("compile", "--output-path", temp, "-t", "helm-string-values")

        configmap_file = os.path.join(
            temp,
            "compiled",
            "helm-string-values",
            "string-values-test",
            "templates",
            "configmap.yaml",
        )
        self.assertTrue(os.path.isfile(configmap_file))

        with open(configmap_file) as fp:
            manifest = yaml.safe_load(fp.read())
            # The numeric string "03190301" should be preserved exactly
            # Currently fails: value becomes "3.190301e+06" (scientific notation)
            numeric_value = manifest["data"]["NUMERIC_STRING"]
            self.assertEqual(
                numeric_value,
                "03190301",
                f"Numeric string was not preserved. Got '{numeric_value}' instead of '03190301'. "
                "This indicates the string was converted to a number and displayed in scientific notation.",
            )

    def test_write_helm_values_file_preserves_numeric_strings(self):
        """
        Unit test for write_helm_values_file to verify that numeric-looking strings
        are written with proper quoting to preserve their string type when read by
        Helm's Go YAML parser (which uses YAML 1.1 rules).

        Related to https://github.com/kapicorp/kapitan/issues/1370

        The issue: Python's yaml.safe_dump writes "03190301" unquoted because Python's
        YAML parser knows it's not a valid octal (contains 8 and 9). However, Helm's
        Go YAML parser interprets unquoted "03190301" as an integer 3190301, which
        then gets displayed in scientific notation for large values.

        The fix requires setting helm_values_quote_strings: true in the compile config.
        """
        # Test values with numeric-looking strings
        helm_values = {
            "leading_zero": "03190301",  # Leading zero string - causes the bug
            "octal_like": "0755",  # Octal-looking string
            "all_zeros": "00000000",  # All zeros string
            "normal_string": "hello",  # Normal string for comparison
            "actual_number": 12345,  # Actual number
        }

        values_file = write_helm_values_file(helm_values)

        # Read the file content to check how it's written
        with open(values_file) as fp:
            content = fp.read()

        # The key check: verify that numeric-looking strings are QUOTED in the YAML output
        # This is what matters for Helm's Go YAML parser

        # Check that leading_zero string is quoted (single or double quotes)
        self.assertTrue(
            "'03190301'" in content or '"03190301"' in content,
            f"Leading zero string '03190301' should be quoted in YAML output to prevent "
            f"Helm (Go YAML) from parsing it as an integer. Current YAML content:\n{content}",
        )

    def test_safe_load_all_filters_none_docs(self):
        """Empty YAML documents (None) from multi-doc streams should be filtered out.

        When Helm charts contain comments before the first ``---`` or between
        documents, ``yaml.safe_load_all`` yields ``None`` entries. These empty
        documents cause kubectl to reject the output with:
          "error converting YAML to JSON: yaml: did not find expected node content"

        https://github.com/kapicorp/kapitan/issues/1396
        """
        yaml_content = "# comment before first doc\n---\napiVersion: v1\nkind: ConfigMap\n---\n# comment between docs\n---\napiVersion: v1\nkind: Secret\n"
        docs = [
            doc
            for doc in yaml.safe_load_all(io.StringIO(yaml_content))
            if doc is not None
        ]
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["kind"], "ConfigMap")
        self.assertEqual(docs[1]["kind"], "Secret")

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class HelmVersionTest(unittest.TestCase):
    """Cover the ``helm version`` probe that backs cache-key version mixing."""

    def setUp(self):
        from kapitan.helm_cli import helm_version

        helm_version.cache_clear()

    def tearDown(self):
        from kapitan.helm_cli import helm_version

        helm_version.cache_clear()

    def test_returns_unresolved_sentinel_for_missing_binary(self):
        from kapitan.helm_cli import helm_version

        result = helm_version("/nonexistent/helm-binary-12345")
        self.assertTrue(result.startswith("unresolved:"))
        self.assertIn("helm-binary-12345", result)

    def test_memoizes_per_resolved_binary(self):
        from unittest.mock import patch

        from kapitan.helm_cli import helm_version

        with patch("kapitan.helm_cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b"v3.19.5+g4a19a5b\n"

            helm_version("/path/to/helm-a")
            helm_version("/path/to/helm-a")  # cached
            helm_version("/path/to/helm-b")  # distinct path → new call

            self.assertEqual(mock_run.call_count, 2)

    def test_helm_version_returns_real_version(self):
        """When the real helm binary is on PATH, return its actual version string."""
        from shutil import which

        from kapitan.helm_cli import helm_version

        if not which("helm"):
            self.skipTest("helm not on PATH")

        result = helm_version()
        # helm version --short emits like "v3.19.5+g4a19a5b"
        self.assertTrue(result.startswith("v"))
        self.assertFalse(result.startswith("unresolved:"))


@pytest.mark.usefixtures("reset_cached_args")
class HelmChartCacheTest(unittest.TestCase):
    """HelmChart() must short-circuit the helm subprocess when its actual
    inputs (chart_dir, helm_values, helm_params, helm_path) are unchanged —
    even if the surrounding kadet cache missed because of an unrelated
    inventory edit.
    """

    def _make_chart_dir(self, root, version="1.0.0", template_body="kind: Deployment"):
        chart_dir = root / "charts" / "demo"
        (chart_dir / "templates").mkdir(parents=True, exist_ok=True)
        (chart_dir / "Chart.yaml").write_text(
            f"apiVersion: v2\nname: demo\nversion: {version}\n"
        )
        (chart_dir / "templates" / "deploy.yaml").write_text(template_body)
        return chart_dir

    def _enable_cache(self):
        from argparse import Namespace

        from kapitan import cached

        cached.args = Namespace(cache=True)
        cached.kapitan_input_helm = None  # force re-init under XDG_CACHE_HOME

    def test_cache_hit_skips_render(self):
        """Second HelmChart() with identical inputs must NOT shell out to helm."""
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            self._make_chart_dir(Path(tmp))
            os.environ["XDG_CACHE_HOME"] = tmp  # isolate the on-disk cache
            self._enable_cache()

            chart_dir = str(Path(tmp) / "charts" / "demo")
            docs = [
                {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "x"}}
            ]

            with (
                patch(
                    "kapitan.inputs.helm.render_chart", return_value=("", "")
                ) as mock_render,
                patch(
                    "kapitan.inputs.helm.yaml.safe_load_all",
                    side_effect=lambda *_a, **_kw: iter(docs),
                ),
            ):
                HelmChart(chart_dir=chart_dir)  # new() calls load_chart()
                self.assertEqual(mock_render.call_count, 1)

            # Second instantiation with the same inputs must hit the cache.
            with patch("kapitan.inputs.helm.render_chart") as mock_render_second:
                second = HelmChart(chart_dir=chart_dir)
                mock_render_second.assert_not_called()
                # And the cached docs reach .root via new().
                self.assertTrue(len(second.root) > 0)

    def test_different_helm_values_force_re_render(self):
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            self._make_chart_dir(Path(tmp))
            os.environ["XDG_CACHE_HOME"] = tmp
            self._enable_cache()

            chart_dir = str(Path(tmp) / "charts" / "demo")
            docs = [
                {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "x"}}
            ]

            with (
                patch(
                    "kapitan.inputs.helm.render_chart", return_value=("", "")
                ) as mock_render,
                patch(
                    "kapitan.inputs.helm.yaml.safe_load_all",
                    side_effect=lambda *_a, **_kw: iter(docs),
                ),
            ):
                HelmChart(chart_dir=chart_dir, helm_values={"a": 1})
                HelmChart(chart_dir=chart_dir, helm_values={"a": 2})
                # Different helm_values → distinct cache keys → render runs twice.
                self.assertEqual(mock_render.call_count, 2)

                # Reusing the first values now hits the cache.
                HelmChart(chart_dir=chart_dir, helm_values={"a": 1})
                self.assertEqual(mock_render.call_count, 2)

    def test_chart_file_edit_invalidates_cache(self):
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            chart_dir = self._make_chart_dir(Path(tmp))
            os.environ["XDG_CACHE_HOME"] = tmp
            self._enable_cache()

            docs = [
                {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "x"}}
            ]

            with (
                patch(
                    "kapitan.inputs.helm.render_chart", return_value=("", "")
                ) as mock_render,
                patch(
                    "kapitan.inputs.helm.yaml.safe_load_all",
                    side_effect=lambda *_a, **_kw: iter(docs),
                ),
            ):
                HelmChart(chart_dir=str(chart_dir))
                self.assertEqual(mock_render.call_count, 1)

                # Edit a template file under the chart_dir.
                (chart_dir / "templates" / "deploy.yaml").write_text("kind: Service\n")
                # Bust the per-process kv memo so the new file digest is read fresh.
                from kapitan import cached as _cached

                _cached.kapitan_input_helm.kv_cache.clear()

                HelmChart(chart_dir=str(chart_dir))
                self.assertEqual(mock_render.call_count, 2)

    def test_helm_version_change_invalidates_cache(self):
        """Same chart_dir + helm_values + helm_params but a new helm binary
        version must bust the cache (e.g. user ran `brew upgrade helm`)."""
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            chart_dir = self._make_chart_dir(Path(tmp))
            os.environ["XDG_CACHE_HOME"] = tmp
            self._enable_cache()

            docs = [
                {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "x"}}
            ]

            with (
                patch(
                    "kapitan.inputs.helm.render_chart", return_value=("", "")
                ) as mock_render,
                patch(
                    "kapitan.inputs.helm.yaml.safe_load_all",
                    side_effect=lambda *_a, **_kw: iter(docs),
                ),
                patch("kapitan.inputs.helm.helm_version", return_value="v3.18.0+gabc"),
            ):
                HelmChart(chart_dir=str(chart_dir))
                self.assertEqual(mock_render.call_count, 1)

            # Simulate a helm upgrade: same path/inputs, different version output.
            with (
                patch(
                    "kapitan.inputs.helm.render_chart", return_value=("", "")
                ) as mock_render_v2,
                patch(
                    "kapitan.inputs.helm.yaml.safe_load_all",
                    side_effect=lambda *_a, **_kw: iter(docs),
                ),
                patch("kapitan.inputs.helm.helm_version", return_value="v3.19.5+gdef"),
            ):
                HelmChart(chart_dir=str(chart_dir))
                self.assertEqual(mock_render_v2.call_count, 1)

    def test_cache_disabled_always_renders(self):
        """When ``cached.args.cache`` is falsy, the cache layer must be skipped
        entirely so behaviour is identical to pre-cache versions."""
        from argparse import Namespace
        from pathlib import Path
        from unittest.mock import patch

        from kapitan import cached as _cached

        with tempfile.TemporaryDirectory() as tmp:
            chart_dir = self._make_chart_dir(Path(tmp))
            _cached.args = Namespace(cache=False)
            _cached.kapitan_input_helm = None

            docs = [
                {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "x"}}
            ]

            with (
                patch(
                    "kapitan.inputs.helm.render_chart", return_value=("", "")
                ) as mock_render,
                patch(
                    "kapitan.inputs.helm.yaml.safe_load_all",
                    side_effect=lambda *_a, **_kw: iter(docs),
                ),
            ):
                HelmChart(chart_dir=str(chart_dir))
                HelmChart(chart_dir=str(chart_dir))
                self.assertEqual(mock_render.call_count, 2)
                self.assertIsNone(_cached.kapitan_input_helm)
