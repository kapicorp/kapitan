#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"compile tests"

import contextlib
import filecmp
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


def _diff_directories(dir1, dir2):
    """Return a list of (rel_path, dir1_path, dir2_path) for files that differ.

    Missing files are represented as None in the corresponding slot.
    """
    diff = []
    files1 = {}
    files2 = {}
    for root, _, files in os.walk(dir1):
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), dir1)
            files1[rel] = os.path.join(root, name)
    for root, _, files in os.walk(dir2):
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), dir2)
            files2[rel] = os.path.join(root, name)
    all_files = set(files1.keys()) | set(files2.keys())
    for rel in sorted(all_files):
        if rel not in files1:
            diff.append((rel, None, files2[rel]))
        elif rel not in files2:
            diff.append((rel, files1[rel], None))
        elif not filecmp.cmp(files1[rel], files2[rel], shallow=False):
            diff.append((rel, files1[rel], files2[rel]))
    return diff


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


@pytest.mark.slow
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
        if compiled_dir_hash != test_compiled_dir_hash:
            diffs = _diff_directories(compile_dir, reference_dir)
            msg_lines = [
                f"Compiled directory hash mismatch: {compiled_dir_hash} != {test_compiled_dir_hash}",
                "Differences found:",
            ]
            for rel, compiled_path, ref_path in diffs:
                if compiled_path is None:
                    msg_lines.append(f"  MISSING in compiled: {rel}")
                elif ref_path is None:
                    msg_lines.append(f"  MISSING in reference: {rel}")
                else:
                    msg_lines.append(f"  DIFFER: {rel}")
                    try:
                        with (
                            open(compiled_path, encoding="utf-8") as f1,
                            open(ref_path, encoding="utf-8") as f2,
                        ):
                            compiled_text = f1.read().splitlines(keepends=True)
                            ref_text = f2.read().splitlines(keepends=True)
                        import difflib

                        diff = list(
                            difflib.unified_diff(
                                ref_text,
                                compiled_text,
                                fromfile=f"reference/{rel}",
                                tofile=f"compiled/{rel}",
                            )
                        )
                        if diff:
                            msg_lines.extend(diff[:40])
                            if len(diff) > 40:
                                msg_lines.append(
                                    f"  ... ({len(diff) - 40} more diff lines)"
                                )
                    except Exception as e:
                        msg_lines.append(f"    Could not diff text: {e}")
            self.fail("\n".join(msg_lines))
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

    def test_compile_wildcard_classes(self):
        """Compile target with wildcard class patterns using --enable-class-wildcards.

        Replaces the exact class ``cluster.minikube`` in ``all-glob.yml`` with
        the wildcard ``cluster.min*``.  Because only ``cluster.minikube``
        matches that pattern, the expanded class list is identical and the
        compiled output should match the reference exactly.
        """
        reset_cache()

        target_path = "inventory/targets/all-glob.yml"
        with open(target_path) as f:
            original_text = f.read()
        target = yaml.safe_load(original_text)

        # Replace the exact class with a wildcard that resolves to the same class.
        target["classes"] = ["common", "component.namespace", "cluster.min*"]

        try:
            with open(target_path, "w") as f:
                yaml.dump(target, f)

            kapitan(
                "compile", "-t", "all-glob", "--enable-class-wildcards", *self.extraArgv
            )

            compile_dir = os.path.join(os.getcwd(), "compiled/all-glob")
            reference_dir = os.path.join(
                TEST_PWD, "tests/test_kubernetes_compiled/all-glob"
            )
            compiled_dir_hash = directory_hash(compile_dir)
            test_compiled_dir_hash = directory_hash(reference_dir)
            if compiled_dir_hash != test_compiled_dir_hash:
                diffs = _diff_directories(compile_dir, reference_dir)
                msg_lines = [
                    f"Compiled directory hash mismatch: {compiled_dir_hash} != {test_compiled_dir_hash}",
                    "Differences found:",
                ]
                for rel, compiled_path, ref_path in diffs:
                    if compiled_path is None:
                        msg_lines.append(f"  MISSING in compiled: {rel}")
                    elif ref_path is None:
                        msg_lines.append(f"  MISSING in reference: {rel}")
                    else:
                        msg_lines.append(f"  DIFFER: {rel}")
                        try:
                            with (
                                open(compiled_path, encoding="utf-8") as f1,
                                open(ref_path, encoding="utf-8") as f2,
                            ):
                                compiled_text = f1.read().splitlines(keepends=True)
                                ref_text = f2.read().splitlines(keepends=True)
                            import difflib

                            diff = list(
                                difflib.unified_diff(
                                    ref_text,
                                    compiled_text,
                                    fromfile=f"reference/{rel}",
                                    tofile=f"compiled/{rel}",
                                )
                            )
                            if diff:
                                msg_lines.extend(diff[:40])
                                if len(diff) > 40:
                                    msg_lines.append(
                                        f"  ... ({len(diff) - 40} more diff lines)"
                                    )
                        except Exception as e:
                            msg_lines.append(f"    Could not diff text: {e}")
                self.fail("\n".join(msg_lines))
            self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)
        finally:
            with open(target_path, "w") as f:
                f.write(original_text)

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


class CompileTestResourcesOCOmegaconf(unittest.TestCase):
    """Test compile with test_resources/omegaconf inventory using omegaconf backend.

    Note: Omegaconf inventory resolution tests are in test_omegaconf.py.
    This class only tests that compilation works with omegaconf backend.
    """

    inventory_path = os.path.join(TEST_PWD, "tests/test_resources/omegaconf")
    extraArgv = ["--inventory-backend=omegaconf"]

    def setUp(self):
        reset_cache()
        os.chdir(self.inventory_path)
        shutil.rmtree("compiled", ignore_errors=True)
        # Register custom resolvers from test_resources/omegaconf
        import sys

        from omegaconf import OmegaConf

        from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers

        inv_path = os.path.join(self.inventory_path, "inventory")
        register_resolvers(inv_path)
        if inv_path not in sys.path:
            sys.path.insert(0, inv_path)
        from resolvers import pass_resolvers

        for name, func in pass_resolvers().items():
            if not OmegaConf.has_resolver(name):
                OmegaConf.register_new_resolver(name, func)

    def test_compile_resolvers_target(self):
        """Test compiling test-resolvers target with omegaconf backend.

        This test verifies that omegaconf inventory resolves correctly
        and compiles without errors (even with empty compile list).
        """
        kapitan("compile", "-t", "test-resolvers", *self.extraArgv)

        # Target should compile successfully (even with empty compile list)
        compiled_dir = os.path.join(self.inventory_path, "compiled/test-resolvers")
        self.assertTrue(
            os.path.exists(compiled_dir),
            f"Expected compiled directory {compiled_dir} to exist",
        )

    def tearDown(self):
        shutil.rmtree("compiled", ignore_errors=True)
        os.chdir(TEST_PWD)
        reset_cache()


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
