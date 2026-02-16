# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import shutil

import pytest
import yaml

from kapitan.inputs.helm import Helm, HelmChart, write_helm_values_file
from kapitan.inputs.kadet import BaseObj
from kapitan.inventory.model.input_types import KapitanInputTypeHelmConfig
from tests.support.helpers import (
    CompileTestHelper,
    assert_compiled_output_exists,
    read_yaml_file,
)


pytestmark = pytest.mark.requires_helm

if shutil.which("helm") is None:
    pytest.skip("helm binary not found", allow_module_level=True)


@pytest.fixture
def helm_env(isolated_helm_project):
    helper = CompileTestHelper(isolated_helm_project)
    return helper


def test_render_chart(helm_env, temp_dir):
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
    assert not error_message
    assert os.path.isfile(
        os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "secrets.yaml")
    )
    assert os.path.isfile(
        os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "deployment.yaml")
    )


def test_error_invalid_chart_dir(helm_env, temp_dir):
    chart_path = "./non-existent"
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
    assert "path" in error_message
    assert "not found" in error_message


def test_compile_chart(helm_env, temp_dir):
    helm_env.compile_with_args(
        ["compile", "--output-path", temp_dir, "-t", "acs-engine-autoscaler"]
    )
    assert os.path.isfile(
        os.path.join(
            temp_dir,
            "compiled",
            "acs-engine-autoscaler",
            "acs-engine-autoscaler",
            "templates",
            "secrets.yaml",
        )
    )


def test_compile_subcharts(helm_env, temp_dir):
    helm_env.compile_with_args(["compile", "--output-path", temp_dir, "-t", "istio"])
    assert os.path.isdir(os.path.join(temp_dir, "compiled", "istio", "istio", "charts"))
    assert os.path.isdir(
        os.path.join(temp_dir, "compiled", "istio", "istio", "templates")
    )


def test_compile_multiple_targets(helm_env, temp_dir):
    helm_env.compile_with_args(
        [
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
    assert os.path.isfile(
        os.path.join(
            temp_dir,
            "compiled",
            "acs-engine-autoscaler",
            "acs-engine-autoscaler",
            "templates",
            "secrets.yaml",
        )
    )
    assert os.path.isfile(
        os.path.join(
            temp_dir,
            "compiled",
            "nginx-ingress",
            "nginx-ingress",
            "templates",
            "clusterrolebinding.yaml",
        )
    )


def test_compile_multiple_charts_per_target(helm_env, temp_dir):
    helm_env.compile_with_args(
        ["compile", "--output-path", temp_dir, "-t", "nginx-istio"]
    )
    assert os.path.isdir(
        os.path.join(temp_dir, "compiled", "nginx-istio", "istio", "templates")
    )
    assert os.path.isdir(
        os.path.join(temp_dir, "compiled", "nginx-istio", "nginx-ingress", "templates")
    )


def test_compile_with_helm_values(helm_env, temp_dir):
    helm_env.compile_with_args(
        ["compile", "--output-path", temp_dir, "-t", "nginx-ingress"]
    )
    controller_deployment_file = assert_compiled_output_exists(
        temp_dir,
        "nginx-ingress/nginx-ingress/templates/controller-deployment.yaml",
    )
    manifest = read_yaml_file(controller_deployment_file)
    name = manifest["metadata"]["name"]
    assert name == "release-name-nginx-ingress-my-controller"


def test_compile_with_helm_values_files(helm_env, temp_dir):
    helm_env.compile_with_args(
        ["compile", "--output-path", temp_dir, "-t", "monitoring-dev", "monitoring-prd"]
    )
    dev_server_deployment_file = assert_compiled_output_exists(
        temp_dir,
        "monitoring-dev/prometheus/templates/server-deployment.yaml",
    )
    prd_server_deployment_file = assert_compiled_output_exists(
        temp_dir,
        "monitoring-prd/prometheus/templates/server-deployment.yaml",
    )

    dev_manifest = read_yaml_file(dev_server_deployment_file)
    assert dev_manifest["metadata"]["name"] == "prometheus-dev-server"

    prd_manifest = read_yaml_file(prd_server_deployment_file)
    assert prd_manifest["metadata"]["name"] == "prometheus-prd-server"


def test_compile_with_helm_params(helm_env, temp_dir):
    argv = [
        "compile",
        "--output-path",
        temp_dir,
        "-t",
        "nginx-ingress-helm-params",
    ]
    with open(
        "inventory/targets/nginx-ingress-helm-params.yml", encoding="utf-8"
    ) as fp:
        manifest = yaml.safe_load(fp.read())
        helm_params = manifest["parameters"]["kapitan"]["compile"][0]["helm_params"]
        release_name = helm_params["name"]
        namespace = helm_params["namespace"]

    helm_env.compile_with_args(argv)
    controller_deployment_file = assert_compiled_output_exists(
        temp_dir,
        "nginx-ingress-helm-params/nginx-ingress/templates/controller-deployment.yaml",
    )
    manifest = read_yaml_file(controller_deployment_file)
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    property = container["args"][4]
    assert property == "--configmap={}/{}".format(
        namespace, release_name + "-nginx-ingress-my-controller"
    )


@pytest.mark.usefixtures("setup_gpg_key")
def test_compile_with_refs(helm_env, temp_dir, gnupg_home, gpg_env):
    helm_env.compile_with_args(
        ["compile", "--output-path", temp_dir, "-t", "nginx-ingress", "--reveal"]
    )
    controller_deployment_file = assert_compiled_output_exists(
        temp_dir,
        "nginx-ingress/nginx-ingress/templates/controller-deployment.yaml",
    )
    manifest = read_yaml_file(controller_deployment_file)
    args = next(
        iter(
            c["args"]
            for c in manifest["spec"]["template"]["spec"]["containers"]
            if c["name"] == "nginx-ingress-my-controller"
        )
    )
    assert "--election-id=super_secret_ID" in args


def test_compile_kadet_helm_chart(helm_env):
    chart = HelmChart(chart_dir="charts/prometheus/")

    assert len(chart.root.keys()) > 0
    for resource_name in chart.root:
        assert isinstance(chart.root[resource_name], BaseObj)


def test_numeric_string_values_preserved(helm_env, temp_dir):
    helm_env.compile_with_args(
        ["compile", "--output-path", temp_dir, "-t", "helm-string-values"]
    )

    configmap_file = assert_compiled_output_exists(
        temp_dir,
        "helm-string-values/string-values-test/templates/configmap.yaml",
    )
    manifest = read_yaml_file(configmap_file)
    numeric_value = manifest["data"]["NUMERIC_STRING"]
    assert numeric_value == "03190301"


def test_write_helm_values_file_preserves_numeric_strings():
    helm_values = {
        "leading_zero": "03190301",
        "octal_like": "0755",
        "all_zeros": "00000000",
        "normal_string": "hello",
        "actual_number": 12345,
    }

    values_file = write_helm_values_file(helm_values)

    with open(values_file, encoding="utf-8") as fp:
        content = fp.read()

    assert "'03190301'" in content or '"03190301"' in content
