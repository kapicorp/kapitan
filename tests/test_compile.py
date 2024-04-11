#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"compile tests"

import unittest
import os
import sys
import io
import contextlib
import glob
import shutil
import yaml
import toml
from kapitan.cli import main
from kapitan.resources import get_inventory
from kapitan.utils import directory_hash
from kapitan.cached import reset_cache
from kapitan.targets import validate_matching_target_name
from kapitan.errors import InventoryError


class CompileTestResourcesTestObjs(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/tests/test_resources/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-t", "test-objects"]
        main()

    def test_plain_ref_revealed(self):
        "check plain refs are revealed in test-objects"
        for g in glob.glob("compiled/test-objects/*.json"):
            with open(g) as f:
                self.assertTrue("?{plain:" not in f.read())

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


class CompileTestResourcesTestKadet(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/tests/test_resources/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-t", "kadet-test"]
        main()

    def test_compile_with_input_params(self):
        # input_params propagate through and written out to file
        for g in glob.glob("compiled/kadet-test/test-1/*.yaml"):
            with open(g, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                team_name = manifest["metadata"]["labels"]["team_name"]
                self.assertEqual(namespace, "ops")
                self.assertEqual(team_name, "client-operations")
        # same kadet function was called with new params should have
        # different results
        for g in glob.glob("compiled/kadet-test/test-2/*.yaml"):
            with open(g, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                team_name = manifest["metadata"]["labels"]["team_name"]
                self.assertEqual(namespace, "team-2")
                self.assertEqual(team_name, "SRE")

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()

class FailCompileTestResourcesTestKadet(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/tests/test_resources/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-t", "fail-compile"]
        main()

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()
        
class CompileTestResourcesTestJinja2InputParams(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/tests/test_resources/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-t", "jinja2-input-params"]
        main()

    def test_compile_with_input_params(self):
        # input_params propagate through and written out to file
        for g in glob.glob("compiled/jinja2-input-params/test-1/*.yml"):
            with open(g, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                name = manifest["metadata"]["name"]
                self.assertEqual(namespace, "ns1")
                self.assertEqual(name, "test1")
        # same jinja2 function was called with new params should have
        # different results
        for g in glob.glob("compiled/jinja2-input-params/test-2/*.yaml"):
            with open(g, "r") as fp:
                manifest = yaml.safe_load(fp.read())
                namespace = manifest["metadata"]["namespace"]
                name = manifest["metadata"]["name"]
                self.assertEqual(namespace, "ns2")
                self.assertEqual(name, "test2")

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


class CompileTestResourcesTestJinja2PostfixStrip(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/tests/test_resources/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-t", "jinja2-postfix-strip"]
        main()

    def test_compile_postfix_strip_disabled(self):
        self.assertListEqual(os.listdir("compiled/jinja2-postfix-strip/unstripped"), ["stub.txt.j2"])

    def test_compile_postfix_strip_overridden(self):
        self.assertListEqual(os.listdir("compiled/jinja2-postfix-strip/stripped-overridden"), ["stub"])

    def test_compile_postfix_strip_enabled(self):
        self.assertListEqual(os.listdir("compiled/jinja2-postfix-strip/stripped"), ["stub.txt"])

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


class CompileKubernetesTest(unittest.TestCase):
    extraArgv = []

    def setUp(self):
        reset_cache()
        os.chdir(os.getcwd() + "/examples/kubernetes/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-c"] + self.extraArgv
        main()
        os.remove("./compiled/.kapitan_cache")
        compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        test_compiled_dir_hash = directory_hash(os.getcwd() + "/../../tests/test_kubernetes_compiled")
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def test_compile_not_enough_args(self):
        with self.assertRaises(SystemExit) as cm:
            # Ignoring stdout for "kapitan --help"
            with contextlib.redirect_stdout(io.StringIO()):
                sys.argv = ["kapitan"]
                main()
        self.assertEqual(cm.exception.code, 1)

    def test_compile_not_matching_targets(self):
        with (
            self.assertLogs(logger="kapitan.targets", level="ERROR") as cm,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            # as of now, we cannot capture stdout with contextlib.redirect_stdout
            # since we only do logger.error(e) in targets.py before exiting
            with self.assertRaises(SystemExit) as ca:
                unmatched_filename = "inventory/targets/minikube-es-fake.yml"
                correct_filename = "inventory/targets/minikube-es.yml"
                os.rename(src=correct_filename, dst=unmatched_filename)
                sys.argv = ["kapitan", "compile"] + self.extraArgv

                try:
                    main()
                finally:
                    # correct the filename again, even if assertion fails
                    if os.path.exists(unmatched_filename):
                        os.rename(src=unmatched_filename, dst=correct_filename)
        error_message_substr = "is missing the corresponding yml file"
        self.assertTrue(" ".join(cm.output).find(error_message_substr) != -1)

    def test_compile_vars_target_missing(self):
        inventory_path = "inventory"
        target_filename = "minikube-es"
        target_obj = get_inventory(inventory_path).get_parameters(target_filename)["kapitan"]
        # delete vars.target
        del target_obj["vars"]["target"]

        with self.assertRaises(InventoryError) as ie:
            validate_matching_target_name(target_filename, target_obj, inventory_path)

        error_message = (
            'Target missing: target "{}" is missing parameters.kapitan.vars.target\n'
            "This parameter should be set to the target name"
        )
        self.assertTrue(error_message.format(target_filename), ie.exception.args[0])

    def test_compile_specific_target(self):
        shutil.rmtree("compiled")
        sys.argv = ["kapitan", "compile", "-t", "minikube-mysql"] + self.extraArgv
        main()
        self.assertTrue(
            os.path.exists("compiled/minikube-mysql") and not os.path.exists("compiled/minikube-es")
        )
        # Reset compiled dir
        sys.argv = ["kapitan", "compile"] + self.extraArgv
        main()

    def test_compile_target_with_label(self):
        shutil.rmtree("compiled")
        sys.argv = ["kapitan", "compile", "-l", "type=kadet"] + self.extraArgv
        main()
        self.assertTrue(
            os.path.exists("compiled/minikube-nginx-kadet")
            and not os.path.exists("compiled/minikube-nginx-jsonnet")
        )
        # Reset compiled dir
        sys.argv = ["kapitan", "compile"] + self.extraArgv
        main()

    def test_compile_jsonnet_env(self):
        shutil.rmtree("compiled")
        sys.argv = ["kapitan", "compile", "-t", "jsonnet-env"] + self.extraArgv
        main()
        self.assertTrue(os.path.exists("compiled/jsonnet-env/jsonnet-env/env.yml"))
        with open("compiled/jsonnet-env/jsonnet-env/env.yml", "r", encoding="utf-8") as f:
            env = dict(yaml.safe_load(f))
            self.assertEqual(set(env.keys()), {"applications", "parameters", "classes", "exports"})
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
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


class CompileKubernetesTestReclassRs(CompileKubernetesTest):
    def setUp(self):
        super().setUp()
        self.extraArgv = ["--inventory-backend=reclass-rs"]

    @unittest.skip("Unnecessary to test with reclass-rs")
    def test_compile_not_enough_args(self):
        pass


class CompileTerraformTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/examples/terraform/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile"]
        main()
        compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        test_compiled_dir_hash = directory_hash(os.getcwd() + "/../../tests/test_terraform_compiled")
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


class PlainOutputTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/examples/docker/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile"]
        main()
        compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        test_compiled_dir_hash = directory_hash(os.getcwd() + "/../../tests/test_docker_compiled")
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


class TomlOutputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.chdir(os.getcwd() + "/tests/test_resources/")
        sys.argv = ["kapitan", "compile", "-t", "toml-output"]
        main()

    def setUp(self):
        target_file_path = os.path.join(os.getcwd(), "inventory/targets/toml-output.yml")
        with open(target_file_path) as target_file:
            target = yaml.safe_load(target_file)
        self.input_parameter = target["parameters"]["input"]

    def test_jsonnet_output(self):
        output_file_path = os.path.join(os.getcwd(), "compiled/toml-output/jsonnet-output/nested.toml")
        expected = self.input_parameter["nested"]

        with open(output_file_path) as output_file:
            output = toml.load(output_file)

        self.assertDictEqual(output, expected)

    def test_kadet_output(self):
        output_file_path = os.path.join(os.getcwd(), "compiled/toml-output/kadet-output/nested.toml")
        expected = self.input_parameter["nested"]

        with open(output_file_path) as output_file:
            output = toml.load(output_file)

        self.assertDictEqual(output, expected)

    @classmethod
    def tearDownClass(cls):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()
