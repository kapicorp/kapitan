# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
import glob
import io
import logging
import os
import shutil
from pathlib import Path

import pytest
import toml
import yaml

from kapitan.cli import main as kapitan
from kapitan.inventory import InventoryBackends
from tests.support.helpers import CompileTestHelper, assert_compiled_output_exists


logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _compile_targets(helper: CompileTestHelper, targets, extra_args=None):
    shutil.rmtree("compiled", ignore_errors=True)
    args = ["compile"]
    if targets:
        args.extend(["-t", *targets])
    if extra_args:
        args.extend(extra_args)
    helper.compile_with_args(args)


def test_compile_no_reveal(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(
        helper,
        ["reveal-output"],
        extra_args=["--reveal", "--no-reveal"],
    )

    output = helper.get_compiled_output("reveal-output/main.json")
    assert "?{gpg:" in output


def test_single_target_compile(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["test-objects"])


def test_plain_ref_revealed(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["test-objects"])

    for path in glob.glob("compiled/test-objects/*.json"):
        with open(path, encoding="utf-8") as handle:
            assert "?{plain:" not in handle.read()


def test_kadet_compile(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["kadet-test"])


def test_kadet_compile_with_input_params(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["kadet-test"])

    # input_params propagate through and written out to file
    for path in glob.glob("compiled/kadet-test/test-1/*.yaml"):
        with open(path, encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle.read())
            namespace = manifest["metadata"]["namespace"]
            team_name = manifest["metadata"]["labels"]["team_name"]
            assert namespace == "ops"
            assert team_name == "client-operations"

    # same kadet function was called with new params should have
    # different results
    for path in glob.glob("compiled/kadet-test/test-2/*.yaml"):
        with open(path, encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle.read())
            namespace = manifest["metadata"]["namespace"]
            team_name = manifest["metadata"]["labels"]["team_name"]
            assert namespace == "team-2"
            assert team_name == "SRE"


def test_fail_compile_kadet(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["fail-compile"])
    assert os.path.isdir("compiled")


def test_jinja2_input_params_compile(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["jinja2-input-params"])


def test_jinja2_input_params_values(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["jinja2-input-params"])

    # input_params propagate through and written out to file
    for path in glob.glob("compiled/jinja2-input-params/test-1/*.yml"):
        with open(path, encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle.read())
            namespace = manifest["metadata"]["namespace"]
            name = manifest["metadata"]["name"]
            assert namespace == "ns1"
            assert name == "test1"

    # same jinja2 function was called with new params should have
    # different results
    for path in glob.glob("compiled/jinja2-input-params/test-2/*.yaml"):
        with open(path, encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle.read())
            namespace = manifest["metadata"]["namespace"]
            name = manifest["metadata"]["name"]
            assert namespace == "ns2"
            assert name == "test2"


def test_jinja2_postfix_strip(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["jinja2-postfix-strip"])

    assert os.listdir("compiled/jinja2-postfix-strip/unstripped") == ["stub.txt.j2"]
    assert os.listdir("compiled/jinja2-postfix-strip/stripped-overridden") == ["stub"]
    assert os.listdir("compiled/jinja2-postfix-strip/stripped") == ["stub.txt"]


def test_external_input_compile_writes_expected_output(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["external-test"])

    compiled_file = assert_compiled_output_exists(os.getcwd(), "external-test/test.md")
    assert compiled_file.read_text(encoding="utf-8") == "This is going into a file\n"


@pytest.fixture(
    params=[
        InventoryBackends.RECLASS,
        InventoryBackends.RECLASS_RS,
        "omegaconf",
    ]
)
def inventory_backend_args(request, isolated_kubernetes_inventory):
    if request.param == "omegaconf":
        from kapitan.inventory.backends.omegaconf import migrate

        migrate(os.getcwd())
        return ["--inventory-backend=omegaconf"]

    if request.param == InventoryBackends.RECLASS_RS:
        return [f"--inventory-backend={InventoryBackends.RECLASS_RS}"]

    return []


def test_compile_kubernetes(inventory_backend_args):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(["compile", "-c", *inventory_backend_args])

    reference_dir = REPO_ROOT / "tests/test_kubernetes_compiled"
    comparisons = [
        "minikube-es/manifests/es-master.yml",
        "minikube-nginx-jsonnet/manifests/app-deployment.yml",
        "minikube-mysql/manifests/mysql_statefulset.yml",
    ]
    for relative_path in comparisons:
        compiled_file = assert_compiled_output_exists(os.getcwd(), relative_path)
        expected_file = reference_dir / relative_path
        assert compiled_file.read_text(encoding="utf-8") == expected_file.read_text(
            encoding="utf-8"
        )


def test_compile_not_enough_args(isolated_kubernetes_inventory, monkeypatch):
    monkeypatch.setattr("sys.argv", ["kapitan"])
    with pytest.raises(SystemExit) as excinfo:
        with contextlib.redirect_stdout(io.StringIO()):
            kapitan()
    assert excinfo.value.code == 1


def test_compile_specific_target(inventory_backend_args):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(
        ["compile", "-t", "minikube-mysql", *inventory_backend_args]
    )

    assert os.path.exists("compiled/minikube-mysql")
    assert not os.path.exists("compiled/minikube-es")


def test_compile_target_with_label(inventory_backend_args):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(["compile", "-l", "type=kadet", *inventory_backend_args])

    assert os.path.exists("compiled/minikube-nginx-kadet")
    assert not os.path.exists("compiled/minikube-nginx-jsonnet")


def test_compile_copy_input_target(inventory_backend_args):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(["compile", "-t", "busybox", *inventory_backend_args])

    assert_compiled_output_exists(os.getcwd(), "busybox/copy_target")
    assert_compiled_output_exists(os.getcwd(), "busybox/copy/copy_target")


def test_compile_remove_input_target(inventory_backend_args):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(["compile", "-t", "removal", *inventory_backend_args])

    assert not os.path.exists("compiled/removal/copy_target")


def test_compile_jsonnet_env(inventory_backend_args):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(["compile", "-t", "jsonnet-env", *inventory_backend_args])

    env_path = "compiled/jsonnet-env/jsonnet-env/env.yml"
    assert os.path.exists(env_path)

    with open(env_path, encoding="utf-8") as handle:
        env = dict(yaml.safe_load(handle))
        logger.error(env)
        assert set(env.keys()) == {"applications", "parameters", "classes", "exports"}
        assert env["applications"] == ["a", "b", "c"]
        assert env["classes"] == ["common", "jsonnet-env"]
        assert env["parameters"]["a"] == "aaaaa"
        assert env["parameters"]["b"] == "bbbbb"
        assert env["parameters"]["c"] == "ccccc"
        assert env["exports"] == {}


def test_compile_terraform(isolated_terraform_inventory):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(["compile"])

    reference_dir = REPO_ROOT / "tests/test_terraform_compiled"
    comparisons = [
        "project1/terraform/provider.tf.json",
        "project2/terraform/output.tf.json",
        "project3/terraform/modules.tf.json",
    ]
    for relative_path in comparisons:
        compiled_file = assert_compiled_output_exists(os.getcwd(), relative_path)
        expected_file = reference_dir / relative_path
        assert compiled_file.read_text(encoding="utf-8") == expected_file.read_text(
            encoding="utf-8"
        )


def test_compile_docker(isolated_docker_inventory):
    helper = CompileTestHelper(os.getcwd())
    helper.compile_with_args(["compile"])

    reference_dir = REPO_ROOT / "tests/test_docker_compiled"
    comparisons = [
        "docker/jsonnet/Dockerfile.web",
        "docker/jsonnet/Dockerfile.worker",
        "docker/kadet/Dockerfile.web",
    ]
    for relative_path in comparisons:
        compiled_file = assert_compiled_output_exists(os.getcwd(), relative_path)
        expected_file = reference_dir / relative_path
        assert compiled_file.read_text(encoding="utf-8") == expected_file.read_text(
            encoding="utf-8"
        )


@pytest.fixture
def toml_output_env(isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    _compile_targets(helper, ["toml-output"])

    target_file_path = (
        Path(isolated_test_resources) / "inventory/targets/toml-output.yml"
    )
    with target_file_path.open(encoding="utf-8") as target_file:
        target = yaml.safe_load(target_file)

    return target["parameters"]["input"], Path(isolated_test_resources)


def test_toml_jsonnet_output(toml_output_env):
    input_parameter, isolated_path = toml_output_env
    output_file_path = isolated_path / "compiled/toml-output/jsonnet-output/nested.toml"
    expected = input_parameter["nested"]

    with output_file_path.open(encoding="utf-8") as output_file:
        output = toml.load(output_file)

    assert output == expected


def test_toml_kadet_output(toml_output_env):
    input_parameter, isolated_path = toml_output_env
    output_file_path = isolated_path / "compiled/toml-output/kadet-output/nested.toml"
    expected = input_parameter["nested"]

    with output_file_path.open(encoding="utf-8") as output_file:
        output = toml.load(output_file)

    assert output == expected
