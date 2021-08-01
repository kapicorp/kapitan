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
from kapitan.cli import main
from kapitan.utils import directory_hash
from kapitan.cached import reset_cache
from kapitan.targets import validate_matching_target_name
from kapitan.resources import inventory_reclass
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


class CompileKubernetesTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.getcwd() + "/examples/kubernetes/")

    def test_compile(self):
        sys.argv = ["kapitan", "compile", "-c"]
        main()
        # Compile again to verify caching works as expected
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
        with self.assertLogs(logger="kapitan.targets", level="ERROR") as cm, contextlib.redirect_stdout(
            io.StringIO()
        ):
            # as of now, we cannot capture stdout with contextlib.redirect_stdout
            # since we only do logger.error(e) in targets.py before exiting
            with self.assertRaises(SystemExit) as ca:
                unmatched_filename = "inventory/targets/minikube-es-fake.yml"
                correct_filename = "inventory/targets/minikube-es.yml"
                os.rename(src=correct_filename, dst=unmatched_filename)
                sys.argv = ["kapitan", "compile"]

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
        target_obj = inventory_reclass(inventory_path)["nodes"][target_filename]["parameters"]["kapitan"]
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
        sys.argv = ["kapitan", "compile", "-t", "minikube-mysql"]
        main()
        self.assertTrue(
            os.path.exists("compiled/minikube-mysql") and not os.path.exists("compiled/minikube-es")
        )
        # Reset compiled dir
        sys.argv = ["kapitan", "compile"]
        main()

    def test_compile_target_with_label(self):
        shutil.rmtree("compiled")
        sys.argv = ["kapitan", "compile", "-l", "type=kadet"]
        main()
        self.assertTrue(
            os.path.exists("compiled/minikube-nginx-kadet")
            and not os.path.exists("compiled/minikube-nginx-jsonnet")
        )
        # Reset compiled dir
        sys.argv = ["kapitan", "compile"]
        main()

    def tearDown(self):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


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
