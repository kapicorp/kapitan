# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
import io
import logging
from pathlib import Path

import pytest
import toml
import yaml

from kapitan.cli import main as kapitan
from kapitan.inventory import InventoryBackends
from tests.support.paths import (
    DOCKER_COMPILE_GOLDEN,
    KUBERNETES_COMPILE_GOLDEN,
    TERRAFORM_COMPILE_GOLDEN,
)


logger = logging.getLogger(__name__)


def _compile_targets(
    kapitan_runner,
    project_root: Path,
    output_root: Path,
    targets,
    extra_args=None,
):
    argv = ["compile", "--output-path", str(output_root)]
    for target in targets:
        argv.extend(["-t", target])
    if extra_args:
        argv.extend(extra_args)
    kapitan_runner(project_root, argv)


def _compiled_output(
    output_root: Path,
    relative_path: str,
    *,
    compiled_subdir: str | Path | None = None,
) -> Path:
    compiled_path = output_root / "compiled"
    if compiled_subdir:
        compiled_path = compiled_path / compiled_subdir
    compiled_path = compiled_path / relative_path
    assert compiled_path.exists()
    return compiled_path


def _assert_text_content_matches(compiled_file: Path, expected_file: Path) -> None:
    assert compiled_file.read_text(encoding="utf-8").rstrip(
        "\n"
    ) == expected_file.read_text(encoding="utf-8").rstrip("\n")


def test_compile_no_reveal(isolated_test_resources, kapitan_runner, tmp_path):
    project_root = Path(isolated_test_resources)
    _compile_targets(
        kapitan_runner,
        project_root,
        tmp_path,
        ["reveal-output"],
        extra_args=["--reveal", "--no-reveal"],
    )

    output = _compiled_output(tmp_path, "reveal-output/main.json").read_text(
        encoding="utf-8"
    )
    assert "?{gpg:" in output


def test_single_target_compile(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["test-objects"]
    )


def test_plain_ref_revealed(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["test-objects"]
    )

    for compiled_file in (tmp_path / "compiled/test-objects").glob("*.json"):
        assert "?{plain:" not in compiled_file.read_text(encoding="utf-8")


def test_kadet_compile(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["kadet-test"]
    )


def test_kadet_compile_with_input_params(
    isolated_test_resources, kapitan_runner, tmp_path
):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["kadet-test"]
    )

    # input_params propagate through and written out to file
    for compiled_file in (tmp_path / "compiled/kadet-test/test-1").glob("*.yaml"):
        manifest = yaml.safe_load(compiled_file.read_text(encoding="utf-8"))
        namespace = manifest["metadata"]["namespace"]
        team_name = manifest["metadata"]["labels"]["team_name"]
        assert namespace == "ops"
        assert team_name == "client-operations"

    # same kadet function was called with new params should have
    # different results
    for compiled_file in (tmp_path / "compiled/kadet-test/test-2").glob("*.yaml"):
        manifest = yaml.safe_load(compiled_file.read_text(encoding="utf-8"))
        namespace = manifest["metadata"]["namespace"]
        team_name = manifest["metadata"]["labels"]["team_name"]
        assert namespace == "team-2"
        assert team_name == "SRE"


def test_fail_compile_kadet(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["fail-compile"]
    )
    assert (tmp_path / "compiled").is_dir()


def test_jinja2_input_params_compile(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["jinja2-input-params"]
    )


def test_jinja2_input_params_values(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["jinja2-input-params"]
    )

    # input_params propagate through and written out to file
    for compiled_file in (tmp_path / "compiled/jinja2-input-params/test-1").glob(
        "*.yml"
    ):
        manifest = yaml.safe_load(compiled_file.read_text(encoding="utf-8"))
        namespace = manifest["metadata"]["namespace"]
        name = manifest["metadata"]["name"]
        assert namespace == "ns1"
        assert name == "test1"

    # same jinja2 function was called with new params should have
    # different results
    for compiled_file in (tmp_path / "compiled/jinja2-input-params/test-2").glob(
        "*.yaml"
    ):
        manifest = yaml.safe_load(compiled_file.read_text(encoding="utf-8"))
        namespace = manifest["metadata"]["namespace"]
        name = manifest["metadata"]["name"]
        assert namespace == "ns2"
        assert name == "test2"


def test_jinja2_postfix_strip(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner,
        Path(isolated_test_resources),
        tmp_path,
        ["jinja2-postfix-strip"],
    )

    assert [
        path.name
        for path in (tmp_path / "compiled/jinja2-postfix-strip/unstripped").iterdir()
    ] == ["stub.txt.j2"]
    assert [
        path.name
        for path in (
            tmp_path / "compiled/jinja2-postfix-strip/stripped-overridden"
        ).iterdir()
    ] == ["stub"]
    assert [
        path.name
        for path in (tmp_path / "compiled/jinja2-postfix-strip/stripped").iterdir()
    ] == ["stub.txt"]


def test_external_input_compile_writes_expected_output(
    isolated_test_resources, kapitan_runner, tmp_path
):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["external-test"]
    )

    compiled_file = _compiled_output(tmp_path, "external-test/test.md")
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

        migrate(str(isolated_kubernetes_inventory))
        return ["--inventory-backend=omegaconf"]

    if request.param == InventoryBackends.RECLASS_RS:
        return [f"--inventory-backend={InventoryBackends.RECLASS_RS}"]

    return []


def test_compile_kubernetes(
    inventory_backend_args, isolated_kubernetes_inventory, kapitan_runner, tmp_path
):
    project_root = Path(isolated_kubernetes_inventory)
    kapitan_runner(
        project_root,
        ["compile", "--output-path", str(tmp_path), "-c", *inventory_backend_args],
    )

    reference_dir = KUBERNETES_COMPILE_GOLDEN
    comparisons = [
        "minikube-es/manifests/es-master.yml",
        "minikube-nginx-jsonnet/manifests/app-deployment.yml",
        "minikube-mysql/manifests/mysql_statefulset.yml",
    ]
    for relative_path in comparisons:
        compiled_file = _compiled_output(tmp_path, relative_path)
        expected_file = reference_dir / relative_path
        _assert_text_content_matches(compiled_file, expected_file)


def test_compile_not_enough_args(isolated_kubernetes_inventory, monkeypatch):
    monkeypatch.setattr("sys.argv", ["kapitan"])
    with pytest.raises(SystemExit) as excinfo:
        with contextlib.redirect_stdout(io.StringIO()):
            kapitan()
    assert excinfo.value.code == 1


def test_compile_specific_target(
    inventory_backend_args, isolated_kubernetes_inventory, kapitan_runner, tmp_path
):
    kapitan_runner(
        Path(isolated_kubernetes_inventory),
        [
            "compile",
            "--output-path",
            str(tmp_path),
            "-t",
            "minikube-mysql",
            *inventory_backend_args,
        ],
    )

    assert (tmp_path / "compiled/minikube-mysql").exists()
    assert not (tmp_path / "compiled/minikube-es").exists()


def test_compile_target_with_label(
    inventory_backend_args, isolated_kubernetes_inventory, kapitan_runner, tmp_path
):
    kapitan_runner(
        Path(isolated_kubernetes_inventory),
        [
            "compile",
            "--output-path",
            str(tmp_path),
            "-l",
            "type=kadet",
            *inventory_backend_args,
        ],
    )

    assert (tmp_path / "compiled/minikube-nginx-kadet").exists()
    assert not (tmp_path / "compiled/minikube-nginx-jsonnet").exists()


def test_compile_copy_input_target(
    inventory_backend_args, isolated_kubernetes_inventory, kapitan_runner, tmp_path
):
    kapitan_runner(
        Path(isolated_kubernetes_inventory),
        [
            "compile",
            "--output-path",
            str(tmp_path),
            "-t",
            "busybox",
            *inventory_backend_args,
        ],
    )

    _compiled_output(tmp_path, "busybox/copy_target")
    _compiled_output(tmp_path, "busybox/copy/copy_target")


def test_compile_remove_input_target(
    inventory_backend_args, isolated_kubernetes_inventory, kapitan_runner, tmp_path
):
    kapitan_runner(
        Path(isolated_kubernetes_inventory),
        [
            "compile",
            "--output-path",
            str(tmp_path),
            "-t",
            "removal",
            *inventory_backend_args,
        ],
    )

    assert not (tmp_path / "compiled/removal/copy_target").exists()


def test_compile_jsonnet_env(
    inventory_backend_args, isolated_kubernetes_inventory, kapitan_runner, tmp_path
):
    kapitan_runner(
        Path(isolated_kubernetes_inventory),
        [
            "compile",
            "--output-path",
            str(tmp_path),
            "-t",
            "jsonnet-env",
            *inventory_backend_args,
        ],
    )

    env_path = tmp_path / "compiled/jsonnet-env/jsonnet-env/env.yml"
    assert env_path.exists()

    env = dict(yaml.safe_load(env_path.read_text(encoding="utf-8")))
    logger.error(env)
    assert set(env.keys()) == {"applications", "parameters", "classes", "exports"}
    assert env["applications"] == ["a", "b", "c"]
    assert env["classes"] == ["common", "jsonnet-env"]
    assert env["parameters"]["a"] == "aaaaa"
    assert env["parameters"]["b"] == "bbbbb"
    assert env["parameters"]["c"] == "ccccc"
    assert env["exports"] == {}


def test_compile_terraform(isolated_terraform_inventory, kapitan_runner, tmp_path):
    kapitan_runner(
        Path(isolated_terraform_inventory), ["compile", "--output-path", str(tmp_path)]
    )

    reference_dir = TERRAFORM_COMPILE_GOLDEN
    comparisons = [
        "project1/terraform/provider.tf.json",
        "project2/terraform/output.tf.json",
        "project3/terraform/modules.tf.json",
    ]
    for relative_path in comparisons:
        compiled_file = _compiled_output(tmp_path, relative_path)
        expected_file = reference_dir / relative_path
        _assert_text_content_matches(compiled_file, expected_file)


def test_compile_docker(isolated_docker_inventory, kapitan_runner, tmp_path):
    kapitan_runner(
        Path(isolated_docker_inventory), ["compile", "--output-path", str(tmp_path)]
    )

    reference_dir = DOCKER_COMPILE_GOLDEN
    comparisons = [
        "jsonnet/Dockerfile.web",
        "jsonnet/Dockerfile.worker",
        "kadet/Dockerfile.web",
    ]
    for relative_path in comparisons:
        compiled_file = _compiled_output(
            tmp_path, relative_path, compiled_subdir="docker"
        )
        expected_file = reference_dir / relative_path
        _assert_text_content_matches(compiled_file, expected_file)


@pytest.fixture
def toml_output_env(isolated_test_resources, kapitan_runner, tmp_path):
    _compile_targets(
        kapitan_runner, Path(isolated_test_resources), tmp_path, ["toml-output"]
    )

    target_file_path = (
        Path(isolated_test_resources) / "inventory/targets/toml-output.yml"
    )
    with target_file_path.open(encoding="utf-8") as target_file:
        target = yaml.safe_load(target_file)

    return target["parameters"]["input"], tmp_path


def test_toml_jsonnet_output(toml_output_env):
    input_parameter, output_root = toml_output_env
    output_file_path = output_root / "compiled/toml-output/jsonnet-output/nested.toml"
    expected = input_parameter["nested"]

    with output_file_path.open(encoding="utf-8") as output_file:
        output = toml.load(output_file)

    assert output == expected


def test_toml_kadet_output(toml_output_env):
    input_parameter, output_root = toml_output_env
    output_file_path = output_root / "compiled/toml-output/kadet-output/nested.toml"
    expected = input_parameter["nested"]

    with output_file_path.open(encoding="utf-8") as output_file:
        output = toml.load(output_file)

    assert output == expected
