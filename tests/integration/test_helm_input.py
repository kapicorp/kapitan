# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import shutil
from pathlib import Path

import pytest
import yaml

from kapitan.inputs.helm import Helm, HelmChart, write_helm_values_file
from kapitan.inputs.kadet import BaseObj
from kapitan.inventory.model.input_types import KapitanInputTypeHelmConfig
from tests.support.helpers import (
    CompileTestHelper,
    assert_compiled_output_exists,
    read_yaml_file,
    run_kapitan_in_project,
)


pytestmark = pytest.mark.requires_helm

if shutil.which("helm") is None:
    pytest.skip("helm binary not found", allow_module_level=True)


@pytest.fixture
def helm_env(isolated_helm_project):
    return CompileTestHelper(isolated_helm_project)


def test_render_chart(helm_env, tmp_path):
    chart_path = helm_env.isolated_path / "charts" / "acs-engine-autoscaler"
    helm_params = {"name": "acs-engine-autoscaler"}
    helm_config = KapitanInputTypeHelmConfig(
        input_paths=[str(chart_path)],
        helm_params=helm_params,
        output_path=str(tmp_path),
    )
    helm = Helm(None, None, None, None, None)
    _, error_message = helm.render_chart(
        str(chart_path),
        str(tmp_path),
        helm_config.helm_path,
        helm_config.helm_params,
        None,
        None,
    )
    assert not error_message
    assert (tmp_path / "acs-engine-autoscaler/templates/secrets.yaml").is_file()
    assert (tmp_path / "acs-engine-autoscaler/templates/deployment.yaml").is_file()


def test_error_invalid_chart_dir(helm_env, tmp_path):
    chart_path = "./non-existent"
    helm_params = {"name": "mychart"}
    helm_config = KapitanInputTypeHelmConfig(
        input_paths=[chart_path], output_path=str(tmp_path), helm_params=helm_params
    )
    helm = Helm(None, None, None, None, None)
    _, error_message = helm.render_chart(
        chart_path,
        str(tmp_path),
        helm_config.helm_path,
        helm_config.helm_params,
        None,
        None,
    )
    assert "path" in error_message
    assert "not found" in error_message


def test_compile_chart(helm_env, tmp_path):
    run_kapitan_in_project(
        helm_env.isolated_path,
        ["compile", "--output-path", str(tmp_path), "-t", "acs-engine-autoscaler"],
    )
    assert (
        tmp_path
        / "compiled/acs-engine-autoscaler/acs-engine-autoscaler/templates/secrets.yaml"
    ).is_file()


def test_compile_subcharts(helm_env, tmp_path):
    run_kapitan_in_project(
        helm_env.isolated_path,
        ["compile", "--output-path", str(tmp_path), "-t", "istio"],
    )
    assert (tmp_path / "compiled/istio/istio/charts").is_dir()
    assert (tmp_path / "compiled/istio/istio/templates").is_dir()


def test_compile_multiple_targets(helm_env, tmp_path):
    run_kapitan_in_project(
        helm_env.isolated_path,
        [
            "compile",
            "--output-path",
            str(tmp_path),
            "-t",
            "acs-engine-autoscaler",
            "nginx-ingress",
            "-p",
            "2",
        ],
    )
    assert (
        tmp_path
        / "compiled/acs-engine-autoscaler/acs-engine-autoscaler/templates/secrets.yaml"
    ).is_file()
    assert (
        tmp_path
        / "compiled/nginx-ingress/nginx-ingress/templates/clusterrolebinding.yaml"
    ).is_file()


def test_compile_multiple_charts_per_target(helm_env, tmp_path):
    run_kapitan_in_project(
        helm_env.isolated_path,
        ["compile", "--output-path", str(tmp_path), "-t", "nginx-istio"],
    )
    assert (tmp_path / "compiled/nginx-istio/istio/templates").is_dir()
    assert (tmp_path / "compiled/nginx-istio/nginx-ingress/templates").is_dir()


def test_compile_with_helm_values(helm_env, tmp_path):
    run_kapitan_in_project(
        helm_env.isolated_path,
        ["compile", "--output-path", str(tmp_path), "-t", "nginx-ingress"],
    )
    controller_deployment_file = assert_compiled_output_exists(
        tmp_path,
        "nginx-ingress/nginx-ingress/templates/controller-deployment.yaml",
    )
    manifest = read_yaml_file(controller_deployment_file)
    name = manifest["metadata"]["name"]
    assert name == "release-name-nginx-ingress-my-controller"


def test_compile_with_helm_values_files(helm_env, tmp_path):
    run_kapitan_in_project(
        helm_env.isolated_path,
        [
            "compile",
            "--output-path",
            str(tmp_path),
            "-t",
            "monitoring-dev",
            "monitoring-prd",
        ],
    )
    dev_server_deployment_file = assert_compiled_output_exists(
        tmp_path,
        "monitoring-dev/prometheus/templates/server-deployment.yaml",
    )
    prd_server_deployment_file = assert_compiled_output_exists(
        tmp_path,
        "monitoring-prd/prometheus/templates/server-deployment.yaml",
    )

    dev_manifest = read_yaml_file(dev_server_deployment_file)
    assert dev_manifest["metadata"]["name"] == "prometheus-dev-server"

    prd_manifest = read_yaml_file(prd_server_deployment_file)
    assert prd_manifest["metadata"]["name"] == "prometheus-prd-server"


def test_compile_with_helm_params(helm_env, tmp_path):
    argv = [
        "compile",
        "--output-path",
        str(tmp_path),
        "-t",
        "nginx-ingress-helm-params",
    ]
    with (
        helm_env.isolated_path
        / "inventory"
        / "targets"
        / "nginx-ingress-helm-params.yml"
    ).open(encoding="utf-8") as fp:
        manifest = yaml.safe_load(fp.read())
        helm_params = manifest["parameters"]["kapitan"]["compile"][0]["helm_params"]
        release_name = helm_params["name"]
        namespace = helm_params["namespace"]

    run_kapitan_in_project(helm_env.isolated_path, argv)
    controller_deployment_file = assert_compiled_output_exists(
        tmp_path,
        "nginx-ingress-helm-params/nginx-ingress/templates/controller-deployment.yaml",
    )
    manifest = read_yaml_file(controller_deployment_file)
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    property = container["args"][4]
    assert property == "--configmap={}/{}".format(
        namespace, release_name + "-nginx-ingress-my-controller"
    )


@pytest.mark.usefixtures("setup_gpg_key")
def test_compile_with_refs(helm_env, tmp_path, gnupg_home, gpg_env):
    run_kapitan_in_project(
        helm_env.isolated_path,
        ["compile", "--output-path", str(tmp_path), "-t", "nginx-ingress", "--reveal"],
    )
    controller_deployment_file = assert_compiled_output_exists(
        tmp_path,
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
    chart = HelmChart(chart_dir=str(helm_env.isolated_path / "charts" / "prometheus"))

    assert len(chart.root.keys()) > 0
    for resource_name in chart.root:
        assert isinstance(chart.root[resource_name], BaseObj)


def test_numeric_string_values_preserved(helm_env, tmp_path):
    run_kapitan_in_project(
        helm_env.isolated_path,
        ["compile", "--output-path", str(tmp_path), "-t", "helm-string-values"],
    )

    configmap_file = assert_compiled_output_exists(
        tmp_path,
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

    with Path(values_file).open(encoding="utf-8") as fp:
        content = fp.read()

    assert "'03190301'" in content or '"03190301"' in content
