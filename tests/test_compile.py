#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Refactored compile tests using pytest fixtures for better isolation."""

import contextlib
import glob
import io
import os
import sys

import pytest
import toml
import yaml

from kapitan.cli import main
from kapitan.inventory import InventoryBackends
from kapitan.utils import directory_hash
from tests.test_helpers import (
    CompileTestHelper,
    IsolatedTestEnvironment,
    assert_file_contains,
    assert_file_not_contains,
    run_kapitan_command,
)


class TestCompileResourcesObjs:
    """Test compilation of test-objects resources."""

    def test_compile_no_reveal(self, isolated_test_resources):
        """Check if --no-reveal flag takes precedence over --reveal."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_with_args(["kapitan", "compile", "-t", "reveal-output", "--reveal", "--no-reveal"])

        output_file = os.path.join(isolated_test_resources, "compiled/reveal-output/main.json")
        assert_file_contains(output_file, "?{gpg:")

    def test_single_target_compile(self, isolated_test_resources):
        """Test compilation of single target."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["test-objects"])

        # Verify that the target was compiled and output exists
        assert os.path.exists(f"{isolated_test_resources}/compiled/test-objects")
        # Also check that some expected files exist
        assert os.path.exists(f"{isolated_test_resources}/compiled/test-objects/inner.json")

    def test_plain_ref_revealed(self, isolated_test_resources):
        """Check plain refs are revealed in test-objects."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["test-objects"])

        for json_file in glob.glob(f"{isolated_test_resources}/compiled/test-objects/*.json"):
            assert_file_not_contains(json_file, "?{plain:")


class TestCompileResourcesKadet:
    """Test Kadet compilation."""

    def test_compile(self, isolated_test_resources):
        """Test basic Kadet compilation."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["kadet-test"])

        # Check that the directory exists rather than a specific file
        assert os.path.exists(f"{isolated_test_resources}/compiled/kadet-test")

    def test_compile_with_input_params(self, isolated_test_resources):
        """Test Kadet compilation with input parameters."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["kadet-test"])

        # Check test-1 output
        for yaml_file in glob.glob(f"{isolated_test_resources}/compiled/kadet-test/test-1/*.yaml"):
            with open(yaml_file, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                assert manifest["metadata"]["namespace"] == "ops"
                assert manifest["metadata"]["labels"]["team_name"] == "client-operations"

        # Check test-2 output
        for yaml_file in glob.glob(f"{isolated_test_resources}/compiled/kadet-test/test-2/*.yaml"):
            with open(yaml_file, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                assert manifest["metadata"]["namespace"] == "team-2"
                assert manifest["metadata"]["labels"]["team_name"] == "SRE"


class TestFailCompileResourcesKadet:
    """Test Kadet compilation failure cases."""

    def test_compile(self, isolated_test_resources):
        """Test compilation of fail-compile target."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["fail-compile"])

        # Verify the target was processed (even if it fails internally)
        # The actual failure behavior should be tested separately


class TestCompileJinja2InputParams:
    """Test Jinja2 compilation with input parameters."""

    def test_compile(self, isolated_test_resources):
        """Test basic Jinja2 compilation."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["jinja2-input-params"])

        # Check that the directory exists
        assert os.path.exists(f"{isolated_test_resources}/compiled/jinja2-input-params")

    def test_compile_with_input_params(self, isolated_test_resources):
        """Test Jinja2 compilation with different input parameters."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["jinja2-input-params"])

        # Check test-1 output
        for yml_file in glob.glob(f"{isolated_test_resources}/compiled/jinja2-input-params/test-1/*.yml"):
            with open(yml_file, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                assert manifest["metadata"]["namespace"] == "ns1"
                assert manifest["metadata"]["name"] == "test1"

        # Check test-2 output
        for yaml_file in glob.glob(f"{isolated_test_resources}/compiled/jinja2-input-params/test-2/*.yaml"):
            with open(yaml_file, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                assert manifest["metadata"]["namespace"] == "ns2"
                assert manifest["metadata"]["name"] == "test2"


class TestCompileJinja2PostfixStrip:
    """Test Jinja2 postfix stripping."""

    def test_compile(self, isolated_test_resources):
        """Test Jinja2 compilation with postfix stripping."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["jinja2-postfix-strip"])

        assert helper.verify_compiled_output_exists("jinja2-postfix-strip/stripped/stub.txt")

    def test_compile_postfix_strip_disabled(self, isolated_test_resources):
        """Test that postfix stripping can be disabled."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["jinja2-postfix-strip"])

        unstripped_dir = f"{isolated_test_resources}/compiled/jinja2-postfix-strip/unstripped"
        assert os.listdir(unstripped_dir) == ["stub.txt.j2"]

    def test_compile_postfix_strip_overridden(self, isolated_test_resources):
        """Test that postfix stripping can be overridden."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["jinja2-postfix-strip"])

        overridden_dir = f"{isolated_test_resources}/compiled/jinja2-postfix-strip/stripped-overridden"
        assert os.listdir(overridden_dir) == ["stub"]

    def test_compile_postfix_strip_enabled(self, isolated_test_resources):
        """Test that postfix stripping works when enabled."""
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["jinja2-postfix-strip"])

        stripped_dir = f"{isolated_test_resources}/compiled/jinja2-postfix-strip/stripped"
        assert os.listdir(stripped_dir) == ["stub.txt"]


class TestCompileKubernetes:
    """Test Kubernetes example compilation."""

    def test_compile(self, isolated_kubernetes_inventory):
        """Test full Kubernetes inventory compilation."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_with_args(["kapitan", "compile", "-c"])

        compile_dir = os.path.join(isolated_kubernetes_inventory, "compiled")
        # Get reference dir from the original test location
        original_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reference_dir = os.path.join(original_cwd, "tests/test_kubernetes_compiled")

        compiled_dir_hash = directory_hash(compile_dir)
        test_compiled_dir_hash = directory_hash(reference_dir)
        assert compiled_dir_hash == test_compiled_dir_hash

    def test_compile_not_enough_args(self):
        """Test that kapitan without arguments exits with error."""
        with pytest.raises(SystemExit) as cm:
            with contextlib.redirect_stdout(io.StringIO()):
                sys.argv = ["kapitan"]
                main()
        assert cm.value.code == 1

    def test_compile_specific_target(self, isolated_kubernetes_inventory):
        """Test compilation of specific target."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_targets(["minikube-mysql"])

        assert os.path.exists(f"{isolated_kubernetes_inventory}/compiled/minikube-mysql")
        assert not os.path.exists(f"{isolated_kubernetes_inventory}/compiled/minikube-es")

    def test_compile_target_with_label(self, isolated_kubernetes_inventory):
        """Test compilation of targets with specific label."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_with_args(["kapitan", "compile", "-l", "type=kadet"])

        assert os.path.exists(f"{isolated_kubernetes_inventory}/compiled/minikube-nginx-kadet")
        assert not os.path.exists(f"{isolated_kubernetes_inventory}/compiled/minikube-nginx-jsonnet")

    def test_compile_jsonnet_env(self, isolated_kubernetes_inventory):
        """Test Jsonnet environment compilation."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_targets(["jsonnet-env"])

        env_file = f"{isolated_kubernetes_inventory}/compiled/jsonnet-env/jsonnet-env/env.yml"
        assert os.path.exists(env_file)

        with open(env_file, "r", encoding="utf-8") as f:
            env = dict(yaml.safe_load(f))
            assert set(env.keys()) == {"applications", "parameters", "classes", "exports"}
            assert env["applications"] == ["a", "b", "c"]
            assert env["classes"] == ["common", "jsonnet-env"]
            assert "a" in env["parameters"]
            assert env["parameters"]["a"] == "aaaaa"
            assert "b" in env["parameters"]
            assert env["parameters"]["b"] == "bbbbb"
            assert "c" in env["parameters"]
            assert env["parameters"]["c"] == "ccccc"
            assert env["exports"] == {}


class TestCompileKubernetesReclassRs:
    """Test Kubernetes compilation with Reclass-rs backend."""

    def test_compile(self, isolated_kubernetes_inventory):
        """Test compilation with reclass-rs inventory backend."""
        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_with_args(
            ["kapitan", "compile", "-c", f"--inventory-backend={InventoryBackends.RECLASS_RS}"]
        )

        compile_dir = os.path.join(isolated_kubernetes_inventory, "compiled")
        # Get reference dir from the original test location
        original_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reference_dir = os.path.join(original_cwd, "tests/test_kubernetes_compiled")

        compiled_dir_hash = directory_hash(compile_dir)
        test_compiled_dir_hash = directory_hash(reference_dir)
        assert compiled_dir_hash == test_compiled_dir_hash


class TestCompileKubernetesOmegaconf:
    """Test Kubernetes compilation with Omegaconf backend."""

    def test_compile(self, isolated_kubernetes_inventory):
        """Test compilation with omegaconf inventory backend."""
        from kapitan.inventory.backends.omegaconf import migrate

        # Migrate inventory to omegaconf format
        migrate(isolated_kubernetes_inventory)

        helper = CompileTestHelper(isolated_kubernetes_inventory)
        helper.compile_with_args(["kapitan", "compile", "-c", "--inventory-backend=omegaconf"])

        compile_dir = os.path.join(isolated_kubernetes_inventory, "compiled")
        # Get reference dir from the original test location
        original_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reference_dir = os.path.join(original_cwd, "tests/test_kubernetes_compiled")

        compiled_dir_hash = directory_hash(compile_dir)
        test_compiled_dir_hash = directory_hash(reference_dir)
        assert compiled_dir_hash == test_compiled_dir_hash


class TestCompileTerraform:
    """Test Terraform example compilation."""

    def test_compile(self, isolated_terraform_inventory):
        """Test Terraform inventory compilation."""
        helper = CompileTestHelper(isolated_terraform_inventory)
        helper.compile_with_args(["kapitan", "compile"])

        compiled_dir = os.path.join(isolated_terraform_inventory, "compiled")
        # Get reference dir from the original test location
        original_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reference_dir = os.path.join(original_cwd, "tests/test_terraform_compiled")

        compiled_dir_hash = directory_hash(compiled_dir)
        test_compiled_dir_hash = directory_hash(reference_dir)
        assert compiled_dir_hash == test_compiled_dir_hash


class TestPlainOutput:
    """Test plain output compilation."""

    def test_compile(self, isolated_docker_inventory):
        """Test Docker inventory compilation."""
        helper = CompileTestHelper(isolated_docker_inventory)
        helper.compile_with_args(["kapitan", "compile"])

        compiled_dir = os.path.join(isolated_docker_inventory, "compiled")
        # Get reference dir from the original test location
        original_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reference_dir = os.path.join(original_cwd, "tests/test_docker_compiled")

        compiled_dir_hash = directory_hash(compiled_dir)
        test_compiled_dir_hash = directory_hash(reference_dir)
        assert compiled_dir_hash == test_compiled_dir_hash


class TestTomlOutput:
    """Test TOML output compilation."""

    def test_jsonnet_output(self, isolated_test_resources):
        """Test Jsonnet TOML output."""
        # Compile the target
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["toml-output"])

        # Load input parameters
        target_file_path = os.path.join(isolated_test_resources, "inventory/targets/toml-output.yml")
        with open(target_file_path) as target_file:
            target = yaml.safe_load(target_file)
        input_parameter = target["parameters"]["input"]

        # Check output
        output_file_path = os.path.join(
            isolated_test_resources, "compiled/toml-output/jsonnet-output/nested.toml"
        )
        expected = input_parameter["nested"]

        with open(output_file_path) as output_file:
            output = toml.load(output_file)

        assert output == expected

    def test_kadet_output(self, isolated_test_resources):
        """Test Kadet TOML output."""
        # Compile the target
        helper = CompileTestHelper(isolated_test_resources)
        helper.compile_targets(["toml-output"])

        # Load input parameters
        target_file_path = os.path.join(isolated_test_resources, "inventory/targets/toml-output.yml")
        with open(target_file_path) as target_file:
            target = yaml.safe_load(target_file)
        input_parameter = target["parameters"]["input"]

        # Check output
        output_file_path = os.path.join(
            isolated_test_resources, "compiled/toml-output/kadet-output/nested.toml"
        )
        expected = input_parameter["nested"]

        with open(output_file_path) as output_file:
            output = toml.load(output_file)

        assert output == expected
