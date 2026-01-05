#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"helm input tests"

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
        sys.argv = [
            "kapitan",
            "compile",
            "--output-path",
            temp,
            "-t",
            "helm-string-values",
        ]
        main()

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

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()
