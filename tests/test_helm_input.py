#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Refactored helm input tests using pytest fixtures for better isolation."""

import os
import sys
import tempfile

import pytest
import yaml

from kapitan.inputs.helm import Helm, HelmChart
from kapitan.inputs.kadet import BaseObj
from kapitan.inventory.model.input_types import KapitanInputTypeHelmConfig
from tests.test_helpers import CompileTestHelper


class TestHelmRender:
    """Test Helm chart rendering."""

    def test_render_chart(self, isolated_test_resources, temp_dir):
        """Test rendering a Helm chart."""
        chart_path = "charts/acs-engine-autoscaler"
        helm_params = {"name": "acs-engine-autoscaler"}
        helm_config = KapitanInputTypeHelmConfig(
            input_paths=[chart_path], helm_params=helm_params, output_path=temp_dir
        )
        helm = Helm(None, None, None, None, None)
        _, error_message = helm.render_chart(
            chart_path, temp_dir, helm_config.helm_path, helm_config.helm_params, None, None
        )
        assert not error_message
        assert os.path.isfile(os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "secrets.yaml"))
        assert os.path.isfile(os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "deployment.yaml"))

    def test_error_invalid_chart_dir(self, temp_dir):
        """Test error handling for invalid chart directory."""
        chart_path = "./non-existent"
        helm_params = {"name": "mychart"}
        helm_config = KapitanInputTypeHelmConfig(
            input_paths=[chart_path], output_path=temp_dir, helm_params=helm_params
        )
        helm = Helm(None, None, None, None, None)
        _, error_message = helm.render_chart(
            chart_path, temp_dir, helm_config.helm_path, helm_config.helm_params, None, None
        )
        assert "path" in error_message and "not found" in error_message


class TestHelmCompile:
    """Test Helm compilation with kapitan compile command."""

    def test_compile_chart(self, isolated_test_resources, temp_dir):
        """Test compiling a single Helm chart."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(
            ["kapitan", "compile", "--output-path", temp_dir, "-t", "acs-engine-autoscaler"]
        )

        expected_file = os.path.join(
            temp_dir,
            "compiled",
            "acs-engine-autoscaler",
            "acs-engine-autoscaler",
            "templates",
            "secrets.yaml",
        )
        assert os.path.isfile(expected_file)

    def test_compile_subcharts(self, isolated_test_resources, temp_dir):
        """Test compiling Helm charts with subcharts."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(["kapitan", "compile", "--output-path", temp_dir, "-t", "istio"])

        assert os.path.isdir(os.path.join(temp_dir, "compiled", "istio", "istio", "charts"))
        assert os.path.isdir(os.path.join(temp_dir, "compiled", "istio", "istio", "templates"))

    def test_compile_multiple_targets(self, isolated_test_resources, temp_dir):
        """Test compiling multiple Helm targets in parallel."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(
            [
                "kapitan",
                "compile",
                "--output-path",
                temp_dir,
                "-t",
                "acs-engine-autoscaler",
                "nginx-ingress",
                "-p",
                "2",
            ]
        )

        # Check acs-engine-autoscaler output
        acs_file = os.path.join(
            temp_dir,
            "compiled",
            "acs-engine-autoscaler",
            "acs-engine-autoscaler",
            "templates",
            "secrets.yaml",
        )
        assert os.path.isfile(acs_file)

        # Check nginx-ingress output
        nginx_file = os.path.join(
            temp_dir, "compiled", "nginx-ingress", "nginx-ingress", "templates", "clusterrolebinding.yaml"
        )
        assert os.path.isfile(nginx_file)

    def test_compile_multiple_charts_per_target(self, isolated_test_resources, temp_dir):
        """Test compiling multiple charts in a single target."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(["kapitan", "compile", "--output-path", temp_dir, "-t", "nginx-istio"])

        assert os.path.isdir(os.path.join(temp_dir, "compiled", "nginx-istio", "istio", "templates"))
        assert os.path.isdir(os.path.join(temp_dir, "compiled", "nginx-istio", "nginx-ingress", "templates"))


class TestHelmValues:
    """Test Helm compilation with different value configurations."""

    def test_compile_with_helm_values(self, isolated_test_resources, temp_dir):
        """Test compilation with Helm values."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(["kapitan", "compile", "--output-path", temp_dir, "-t", "nginx-ingress"])

        controller_deployment_file = os.path.join(
            temp_dir, "compiled", "nginx-ingress", "nginx-ingress", "templates", "controller-deployment.yaml"
        )
        assert os.path.isfile(controller_deployment_file)

        with open(controller_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest["metadata"]["name"]
            assert name == "release-name-nginx-ingress-my-controller"

    def test_compile_with_helm_values_files(self, isolated_test_resources, temp_dir):
        """Test compilation with separate Helm values files."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(
            ["kapitan", "compile", "--output-path", temp_dir, "-t", "monitoring-dev", "monitoring-prd"]
        )

        dev_server_deployment_file = os.path.join(
            temp_dir, "compiled", "monitoring-dev", "prometheus", "templates", "server-deployment.yaml"
        )
        prd_server_deployment_file = os.path.join(
            temp_dir, "compiled", "monitoring-prd", "prometheus", "templates", "server-deployment.yaml"
        )

        # Check dev environment
        assert os.path.isfile(dev_server_deployment_file)
        with open(dev_server_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest["metadata"]["name"]
            assert name == "prometheus-dev-server"

        # Check prd environment
        assert os.path.isfile(prd_server_deployment_file)
        with open(prd_server_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest["metadata"]["name"]
            assert name == "prometheus-prd-server"

    def test_compile_with_helm_params(self, isolated_test_resources, temp_dir):
        """Test compilation with Helm parameters."""
        # Read the target configuration to understand expected values
        with open(
            os.path.join(isolated_test_resources, "inventory/targets/nginx-ingress-helm-params.yml"), "r"
        ) as fp:
            manifest = yaml.safe_load(fp.read())
            helm_params = manifest["parameters"]["kapitan"]["compile"][0]["helm_params"]
            release_name = helm_params["name"]
            namespace = helm_params["namespace"]

        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(
            ["kapitan", "compile", "--output-path", temp_dir, "-t", "nginx-ingress-helm-params"]
        )

        controller_deployment_file = os.path.join(
            temp_dir,
            "compiled",
            "nginx-ingress-helm-params",
            "nginx-ingress",
            "templates",
            "controller-deployment.yaml",
        )

        assert os.path.isfile(controller_deployment_file)
        with open(controller_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            container = manifest["spec"]["template"]["spec"]["containers"][0]
            property = container["args"][4]
            expected_property = "--configmap={}/{}".format(
                namespace, release_name + "-nginx-ingress-my-controller"
            )
            assert property == expected_property

    @pytest.mark.requires_gpg
    def test_compile_with_refs(self, isolated_test_resources, temp_dir, gnupg_home):
        """Test compilation with refs revealed."""
        from tests.test_helpers import setup_gpg_key

        # Setup GPG key for testing
        # Get the project root directory (parent of tests directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        key_path = os.path.join(project_root, "examples/kubernetes/refs/example@kapitan.dev.key")
        setup_gpg_key(key_path, gnupg_home)

        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(
            ["kapitan", "compile", "--output-path", temp_dir, "-t", "nginx-ingress", "--reveal"]
        )

        controller_deployment_file = os.path.join(
            temp_dir, "compiled", "nginx-ingress", "nginx-ingress", "templates", "controller-deployment.yaml"
        )
        assert os.path.isfile(controller_deployment_file)

        with open(controller_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            args = next(
                iter(
                    c["args"]
                    for c in manifest["spec"]["template"]["spec"]["containers"]
                    if c["name"] == "nginx-ingress-my-controller"
                )
            )
            assert "--election-id=super_secret_ID" in args


class TestKadetHelmIntegration:
    """Test Kadet integration with Helm charts."""

    def test_compile_kadet_helm_chart(self, isolated_test_resources):
        """Test rendering Helm chart for Kadet integration."""
        # Render chart
        chart = HelmChart(chart_dir="charts/prometheus/")

        # Number of keys must be greater than 0
        assert len(chart.root.keys()) > 0
        # All values must be BaseObj
        for resource_name in chart.root:
            assert isinstance(chart.root[resource_name], BaseObj)
