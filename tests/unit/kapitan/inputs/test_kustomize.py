# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import shutil

import pytest
import yaml

from kapitan.inputs.kustomize import Kustomize
from kapitan.inventory.model.input_types import KapitanInputTypeKustomizeConfig


pytestmark = pytest.mark.requires_kustomize

if shutil.which("kustomize") is None:
    pytest.skip("kustomize binary not found", allow_module_level=True)


@pytest.fixture
def kustomize_env(tmp_path):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()
    args = type("Args", (), {"kustomize_path": "kustomize"})
    kustomize = Kustomize(
        str(compile_path),
        [],
        None,
        "test-target",
        args,
    )
    return kustomize, compile_path


def _write_yaml(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def test_compile_file_with_patches(kustomize_env, tmp_path):
    kustomize, compile_path = kustomize_env
    temp_dir = tmp_path / "overlay"
    temp_dir.mkdir()

    _write_yaml(
        temp_dir / "kustomization.yaml",
        {"resources": ["deployment.yaml"], "namespace": "test-namespace"},
    )
    _write_yaml(
        temp_dir / "deployment.yaml",
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-deployment", "namespace": "test-namespace"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "test-container", "image": "nginx:latest"}
                        ]
                    }
                }
            },
        },
    )

    patch = {
        "target": {
            "kind": "Deployment",
            "name": "test-deployment",
            "namespace": "test-namespace",
        },
        "patch": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-deployment", "namespace": "test-namespace"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "test-container", "image": "nginx:1.19"}
                        ]
                    }
                }
            },
        },
    }

    config = KapitanInputTypeKustomizeConfig(
        namespace="test-namespace",
        patches={"image-patch": patch},
        input_paths=[str(temp_dir)],
        output_path=str(compile_path),
    )

    kustomize.compile_file(config, str(temp_dir), str(compile_path))

    output_file = compile_path / "test-deployment-deployment.yaml"
    assert output_file.exists()

    with open(output_file, encoding="utf-8") as handle:
        output = yaml.safe_load(handle)
        assert (
            output["spec"]["template"]["spec"]["containers"][0]["image"] == "nginx:1.19"
        )


def test_compile_file_with_namespace(kustomize_env, tmp_path):
    kustomize, compile_path = kustomize_env
    temp_dir = tmp_path / "overlay"
    temp_dir.mkdir()

    _write_yaml(temp_dir / "kustomization.yaml", {"resources": ["deployment.yaml"]})
    _write_yaml(
        temp_dir / "deployment.yaml",
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-deployment"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "test-container", "image": "nginx:latest"}
                        ]
                    }
                }
            },
        },
    )

    config = KapitanInputTypeKustomizeConfig(
        namespace="test-namespace",
        input_paths=[str(temp_dir)],
        output_path=str(compile_path),
    )

    kustomize.compile_file(config, str(temp_dir), str(compile_path))

    output_file = compile_path / "test-deployment-deployment.yaml"
    assert output_file.exists()

    with open(output_file, encoding="utf-8") as handle:
        output = yaml.safe_load(handle)
        assert output["metadata"]["namespace"] == "test-namespace"


def test_compile_file_with_invalid_input(kustomize_env, tmp_path):
    kustomize, compile_path = kustomize_env
    temp_dir = tmp_path / "overlay"
    temp_dir.mkdir()

    _write_yaml(temp_dir / "kustomization.yaml", {"resources": ["nonexistent.yaml"]})

    config = KapitanInputTypeKustomizeConfig(
        namespace="test-namespace",
        input_paths=[str(temp_dir)],
        output_path=str(compile_path),
    )

    with pytest.raises(Exception):
        kustomize.compile_file(config, str(temp_dir), str(compile_path))


def test_compile_file_with_invalid_patch(kustomize_env, tmp_path):
    kustomize, compile_path = kustomize_env
    temp_dir = tmp_path / "overlay"
    temp_dir.mkdir()

    _write_yaml(temp_dir / "kustomization.yaml", {"resources": ["deployment.yaml"]})
    _write_yaml(
        temp_dir / "deployment.yaml",
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-deployment"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "test-container", "image": "nginx:latest"}
                        ]
                    }
                }
            },
        },
    )

    patch = {
        "target": {"kind": "Deployment", "name": "nonexistent-deployment"},
        "patch": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "nonexistent-deployment"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "test-container", "image": "nginx:1.19"}
                        ]
                    }
                }
            },
        },
    }

    config = KapitanInputTypeKustomizeConfig(
        namespace="test-namespace",
        patches={"invalid-patch": patch},
        input_paths=[str(temp_dir)],
        output_path=str(compile_path),
    )

    kustomize.compile_file(config, str(temp_dir), str(compile_path))

    output_file = compile_path / "test-deployment-deployment.yaml"
    assert output_file.exists()

    with open(output_file, encoding="utf-8") as handle:
        output = yaml.safe_load(handle)
        assert (
            output["spec"]["template"]["spec"]["containers"][0]["image"]
            == "nginx:latest"
        )
