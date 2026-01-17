#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"compile tests"

import contextlib
import glob
import io
import logging
import os
import shutil
import unittest

import pytest
import toml
import yaml

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan
from kapitan.inventory import InventoryBackends
from kapitan.utils import directory_hash


logger = logging.getLogger(__name__)

TEST_PWD = os.getcwd()
TEST_RESOURCES_PATH = os.path.join(os.getcwd(), "tests/test_resources")
TEST_DOCKER_PATH = os.path.join(os.getcwd(), "examples/docker/")
TEST_TERRAFORM_PATH = os.path.join(os.getcwd(), "examples/terraform/")
TEST_KUBERNETES_PATH = os.path.join(os.getcwd(), "examples/kubernetes/")


class CompileTestResourcesTestObjs(unittest.TestCase):
    def setUp(self):
        reset_cache()
        os.chdir(TEST_RESOURCES_PATH)

    def test_compile_no_reveal(self):
        # check if the --no-reveal flag takes precedence over --reveal when passed together
        kapitan(
            "compile",
            "-t",
            "reveal-output",
            "--reveal",
            "--no-reveal",
        )

        with open("compiled/reveal-output/main.json") as f:
            self.assertTrue("?{gpg:" in f.read())

    def test_single_target_compile(self):
        kapitan("compile", "-t", "test-objects")

    def test_plain_ref_revealed(self):
        "check plain refs are revealed in test-objects"
        for g in glob.glob("compiled/test-objects/*.json"):
            with open(g) as f:
                self.assertTrue("?{plain:" not in f.read())

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class CompileTestResourcesTestKadet(unittest.TestCase):
    def setUp(self):
        os.chdir(TEST_RESOURCES_PATH)
        reset_cache()

    def test_compile(self):
        kapitan("compile", "-t", "kadet-test")

    def test_compile_with_input_params(self):
        # input_params propagate through and written out to file
        for g in glob.glob("compiled/kadet-test/test-1/*.yaml"):
            with open(g) as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                team_name = manifest["metadata"]["labels"]["team_name"]
                self.assertEqual(namespace, "ops")
                self.assertEqual(team_name, "client-operations")
        # same kadet function was called with new params should have
        # different results
        for g in glob.glob("compiled/kadet-test/test-2/*.yaml"):
            with open(g) as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                team_name = manifest["metadata"]["labels"]["team_name"]
                self.assertEqual(namespace, "team-2")
                self.assertEqual(team_name, "SRE")

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class FailCompileTestResourcesTestKadet(unittest.TestCase):
    def setUp(self):
        os.chdir(TEST_RESOURCES_PATH)
        reset_cache()

    def test_compile(self):
        kapitan("compile", "-t", "fail-compile")

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class CompileTestResourcesTestJinja2InputParams(unittest.TestCase):
    def setUp(self):
        os.chdir(TEST_RESOURCES_PATH)
        reset_cache()

    def test_compile(self):
        kapitan("compile", "-t", "jinja2-input-params")

    def test_compile_with_input_params(self):
        # input_params propagate through and written out to file
        for g in glob.glob("compiled/jinja2-input-params/test-1/*.yml"):
            with open(g) as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                name = manifest["metadata"]["name"]
                self.assertEqual(namespace, "ns1")
                self.assertEqual(name, "test1")
        # same jinja2 function was called with new params should have
        # different results
        for g in glob.glob("compiled/jinja2-input-params/test-2/*.yaml"):
            with open(g) as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                name = manifest["metadata"]["name"]
                self.assertEqual(namespace, "ns2")
                self.assertEqual(name, "test2")

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class CompileTestResourcesTestJinja2PostfixStrip(unittest.TestCase):
    def setUp(self):
        os.chdir(TEST_RESOURCES_PATH)
        reset_cache()

    def test_compile(self):
        kapitan("compile", "-t", "jinja2-postfix-strip")

    def test_compile_postfix_strip_disabled(self):
        self.assertListEqual(
            os.listdir("compiled/jinja2-postfix-strip/unstripped"), ["stub.txt.j2"]
        )

    def test_compile_postfix_strip_overridden(self):
        self.assertListEqual(
            os.listdir("compiled/jinja2-postfix-strip/stripped-overridden"), ["stub"]
        )

    def test_compile_postfix_strip_enabled(self):
        self.assertListEqual(
            os.listdir("compiled/jinja2-postfix-strip/stripped"), ["stub.txt"]
        )

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


@pytest.mark.usefixtures("isolated_kubernetes_inventory")
class CompileKubernetesTest(unittest.TestCase):
    extraArgv = []

    def setUp(self):
        self.inventory_path = os.getcwd()
        reset_cache()
        shutil.rmtree("compiled", ignore_errors=True)

    def test_compile(self):
        kapitan("compile", "-c", *self.extraArgv)
        compile_dir = os.path.join(os.getcwd(), "compiled")
        reference_dir = os.path.join(TEST_PWD, "tests/test_kubernetes_compiled")
        compiled_dir_hash = directory_hash(compile_dir)
        test_compiled_dir_hash = directory_hash(reference_dir)
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def test_compile_not_enough_args(self):
        with self.assertRaises(SystemExit) as cm:
            # Ignoring stdout for "kapitan --help"
            with contextlib.redirect_stdout(io.StringIO()):
                kapitan()
        self.assertEqual(cm.exception.code, 1)

    def test_compile_specific_target(self):
        reset_cache()
        kapitan("compile", "-t", "minikube-mysql", *self.extraArgv)
        self.assertTrue(
            os.path.exists("compiled/minikube-mysql")
            and not os.path.exists("compiled/minikube-es")
        )

    def test_compile_target_with_label(self):
        reset_cache()
        kapitan("compile", "-l", "type=kadet", *self.extraArgv)
        self.assertTrue(
            os.path.exists("compiled/minikube-nginx-kadet")
            and not os.path.exists("compiled/minikube-nginx-jsonnet")
        )

    def test_compile_jsonnet_env(self):
        kapitan("compile", "-t", "jsonnet-env", *self.extraArgv)
        self.assertTrue(os.path.exists("compiled/jsonnet-env/jsonnet-env/env.yml"))
        with open("compiled/jsonnet-env/jsonnet-env/env.yml", encoding="utf-8") as f:
            env = dict(yaml.safe_load(f))
            logger.error(env)
            self.assertEqual(
                set(env.keys()), {"applications", "parameters", "classes", "exports"}
            )
            self.assertEqual(env["applications"], ["a", "b", "c"])
            self.assertEqual(env["classes"], ["common", "jsonnet-env"])
            self.assertTrue("a" in env["parameters"])
            self.assertEqual(env["parameters"]["a"], "aaaaa")
            self.assertTrue("b" in env["parameters"])
            self.assertEqual(env["parameters"]["b"], "bbbbb")
            self.assertTrue("c" in env["parameters"])
            self.assertEqual(env["parameters"]["c"], "ccccc")
            self.assertEqual(env["exports"], {})

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class CompileKubernetesTestReclassRs(CompileKubernetesTest):
    def setUp(self):
        super().setUp()
        self.extraArgv = [f"--inventory-backend={(InventoryBackends.RECLASS_RS)}"]

    @unittest.skip("Already tested")
    def test_compile_not_enough_args(self):
        pass


class CompileKubernetesTestOmegaconf(CompileKubernetesTest):
    def setUp(self):
        super().setUp()
        self.extraArgv = ["--inventory-backend=omegaconf"]
        from kapitan.inventory.backends.omegaconf import migrate

        migrate(os.getcwd())

    @unittest.skip("Already tested")
    def test_compile_not_enough_args(self):
        pass


class CompileTerraformTest(unittest.TestCase):
    def setUp(self):
        os.chdir(TEST_TERRAFORM_PATH)

    def test_compile(self):
        kapitan("compile")
        compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        test_compiled_dir_hash = directory_hash(
            os.getcwd() + "/../../tests/test_terraform_compiled"
        )
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class PlainOutputTest(unittest.TestCase):
    def setUp(self):
        os.chdir(TEST_DOCKER_PATH)

    def test_compile(self):
        kapitan("compile")
        compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        test_compiled_dir_hash = directory_hash(
            os.getcwd() + "/../../tests/test_docker_compiled"
        )
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def tearDown(self):
        os.chdir(TEST_PWD)
        reset_cache()


class TomlOutputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.chdir(TEST_RESOURCES_PATH)
        kapitan("compile", "-t", "toml-output")

    def setUp(self):
        target_file_path = os.path.join(
            os.getcwd(), "inventory/targets/toml-output.yml"
        )
        with open(target_file_path) as target_file:
            target = yaml.safe_load(target_file)
        self.input_parameter = target["parameters"]["input"]

    def test_jsonnet_output(self):
        output_file_path = os.path.join(
            os.getcwd(), "compiled/toml-output/jsonnet-output/nested.toml"
        )
        expected = self.input_parameter["nested"]

        with open(output_file_path) as output_file:
            output = toml.load(output_file)

        self.assertDictEqual(output, expected)

    def test_kadet_output(self):
        output_file_path = os.path.join(
            os.getcwd(), "compiled/toml-output/kadet-output/nested.toml"
        )
        expected = self.input_parameter["nested"]

        with open(output_file_path) as output_file:
            output = toml.load(output_file)

        self.assertDictEqual(output, expected)

    @classmethod
    def tearDownClass(cls):
        os.chdir(TEST_PWD)
        reset_cache()


class CompileTestEmptyKapitanConfig(unittest.TestCase):
    """Test for issue #1379: misleading error when parameters.kapitan.compile is missing"""

    def test_missing_compile_config_no_error(self):
        """Test that targets without compile configuration are skipped gracefully without FileNotFoundError"""
        import tempfile

        test_configs = [
            ("empty-kapitan", "parameters:\n  kapitan: {}"),
            (
                "no-compile-key",
                "parameters:\n  kapitan:\n    vars:\n      target: test-target",
            ),
        ]

        for target_name, target_config in test_configs:
            with self.subTest(config=target_name):
                with tempfile.TemporaryDirectory() as test_dir:
                    inventory_dir = os.path.join(test_dir, "inventory")
                    os.makedirs(os.path.join(inventory_dir, "classes"), exist_ok=True)
                    os.makedirs(os.path.join(inventory_dir, "targets"), exist_ok=True)

                    # Create target with the config
                    with open(
                        os.path.join(inventory_dir, "targets", "test-target.yml"), "w"
                    ) as f:
                        f.write(target_config)

                    original_dir = os.getcwd()
                    try:
                        os.chdir(test_dir)
                        reset_cache()
                        # Should complete without errors, just skip the target
                        with contextlib.redirect_stdout(io.StringIO()):
                            kapitan("compile")

                        # Verify no target directory was compiled
                        compiled_dir = os.path.join(test_dir, "compiled")
                        if os.path.exists(compiled_dir):
                            self.assertFalse(
                                os.path.exists(
                                    os.path.join(compiled_dir, "test-target")
                                )
                            )
                    finally:
                        os.chdir(original_dir)
                        reset_cache()

    def test_mixed_targets_compile_only_valid(self):
        """Test that when mixing valid and invalid targets, only valid ones are compiled"""
        import tempfile

        with tempfile.TemporaryDirectory() as test_dir:
            inventory_dir = os.path.join(test_dir, "inventory")
            os.makedirs(os.path.join(inventory_dir, "classes"), exist_ok=True)
            os.makedirs(os.path.join(inventory_dir, "targets"), exist_ok=True)

            # Create target WITHOUT compile config
            with open(
                os.path.join(inventory_dir, "targets", "no-compile.yml"), "w"
            ) as f:
                f.write("parameters:\n  kapitan: {}")

            # Create target WITH compile config
            with open(
                os.path.join(inventory_dir, "targets", "with-compile.yml"), "w"
            ) as f:
                f.write("""parameters:
  kapitan:
    vars:
      target: with-compile
    compile:
      - output_path: .
        input_type: copy
        input_paths:
          - inventory/targets/with-compile.yml
""")

            original_dir = os.getcwd()
            try:
                os.chdir(test_dir)
                reset_cache()
                # Should compile only the valid target
                with contextlib.redirect_stdout(io.StringIO()):
                    kapitan("compile")

                # Verify only with-compile was compiled
                compiled_dir = os.path.join(test_dir, "compiled")
                self.assertTrue(os.path.exists(compiled_dir))
                self.assertTrue(
                    os.path.exists(os.path.join(compiled_dir, "with-compile"))
                )
                self.assertFalse(
                    os.path.exists(os.path.join(compiled_dir, "no-compile"))
                )

                # Verify the file was actually compiled
                self.assertTrue(
                    os.path.exists(
                        os.path.join(compiled_dir, "with-compile", "with-compile.yml")
                    )
                )
            finally:
                os.chdir(original_dir)
                reset_cache()
