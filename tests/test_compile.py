#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"compile tests"

import contextlib
import glob
import importlib.util
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
TEST_KUBERNETES_COMPILED_PATH = os.path.join(
    os.getcwd(), "tests/test_kubernetes_compiled"
)
TEST_TERRAFORM_COMPILED_PATH = os.path.join(
    os.getcwd(), "tests/test_terraform_compiled"
)
TEST_DOCKER_COMPILED_PATH = os.path.join(os.getcwd(), "tests/test_docker_compiled")


@pytest.mark.usefixtures("isolated_test_resources")
class CompileTestResourcesTestObjs(unittest.TestCase):
    def setUp(self):
        reset_cache()
        kapitan("compile", "-t", "test-objects")
        kapitan("compile", "-t", "reveal-output")

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


@pytest.mark.usefixtures("isolated_test_resources")
class CompileTestResourcesTestKadet(unittest.TestCase):
    def setUp(self):
        reset_cache()
        kapitan("compile", "-t", "kadet-test")

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
        reset_cache()


@pytest.mark.usefixtures("isolated_test_resources")
class FailCompileTestResourcesTestKadet(unittest.TestCase):
    def test_compile(self):
        kapitan("compile", "-t", "fail-compile")


@pytest.mark.usefixtures("isolated_test_resources")
class CompileTestResourcesTestJinja2InputParams(unittest.TestCase):
    def setUp(self):
        reset_cache()
        kapitan("compile", "-t", "jinja2-input-params")

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
        reset_cache()


@pytest.mark.usefixtures("isolated_test_resources")
class CompileTestResourcesTestJinja2PostfixStrip(unittest.TestCase):
    def setUp(self):
        reset_cache()
        kapitan("compile", "-t", "jinja2-postfix-strip")

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


@pytest.mark.usefixtures("isolated_omegaconf_inventory")
class CompileTestResourcesOCOmegaconf(unittest.TestCase):
    """Test compile with test_resources/omegaconf inventory using omegaconf backend.

    Note: Omegaconf inventory resolution tests are in test_omegaconf.py.
    This class only tests that compilation works with omegaconf backend.
    """

    extraArgv = ["--inventory-backend=omegaconf"]

    def setUp(self):
        reset_cache()
        shutil.rmtree("compiled", ignore_errors=True)
        # Register custom resolvers from the isolated omegaconf inventory
        from omegaconf import OmegaConf

        from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers

        inv_path = os.path.join(os.getcwd(), "inventory")
        register_resolvers(inv_path)
        resolvers_spec = importlib.util.spec_from_file_location(
            "resolvers", os.path.join(inv_path, "resolvers.py")
        )
        assert resolvers_spec is not None
        assert resolvers_spec.loader is not None
        resolvers_module = importlib.util.module_from_spec(resolvers_spec)
        resolvers_spec.loader.exec_module(resolvers_module)
        for name, func in resolvers_module.pass_resolvers().items():
            if not OmegaConf.has_resolver(name):
                OmegaConf.register_new_resolver(name, func)

    def test_compile_resolvers_target(self):
        """Test compiling test-resolvers target with omegaconf backend.

        This test verifies that omegaconf inventory resolves correctly
        and compiles without errors (even with empty compile list).
        """
        kapitan("compile", "-t", "test-resolvers", *self.extraArgv)

        # Target should compile successfully (even with empty compile list)
        compiled_dir = os.path.join(os.getcwd(), "compiled/test-resolvers")
        self.assertTrue(
            os.path.exists(compiled_dir),
            f"Expected compiled directory {compiled_dir} to exist",
        )

    def tearDown(self):
        shutil.rmtree("compiled", ignore_errors=True)
        reset_cache()


@pytest.mark.usefixtures("isolated_terraform_inventory")
class CompileTerraformTest(unittest.TestCase):
    def test_compile(self):
        kapitan("compile")
        compiled_dir_hash = directory_hash(os.path.join(os.getcwd(), "compiled"))
        test_compiled_dir_hash = directory_hash(TEST_TERRAFORM_COMPILED_PATH)
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def tearDown(self):
        reset_cache()


@pytest.mark.usefixtures("isolated_docker_inventory")
class PlainOutputTest(unittest.TestCase):
    def test_compile(self):
        kapitan("compile")
        compiled_dir_hash = directory_hash(os.path.join(os.getcwd(), "compiled"))
        test_compiled_dir_hash = directory_hash(TEST_DOCKER_COMPILED_PATH)
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def tearDown(self):
        reset_cache()


@pytest.mark.usefixtures("isolated_test_resources")
class TomlOutputTest(unittest.TestCase):
    def setUp(self):
        reset_cache()
        kapitan("compile", "-t", "toml-output")
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

    def tearDown(self):
        reset_cache()
