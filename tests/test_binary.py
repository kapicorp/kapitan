# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"binary tests"

import base64
import contextlib
from distutils import dir_util
import io
import os
import tempfile
import shutil
import subprocess
import sys
import unittest

from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.utils import directory_hash

REFS_PATH = tempfile.mkdtemp()
BINARY_PATH = "bindist/kapitan-linux-amd64"


@unittest.skipIf(not os.path.exists(BINARY_PATH), "kapitan binary not found")
class BinaryTest(unittest.TestCase):
    def test_cli_secret_validate_targets(self):
        """
        run $ kapitan refs --validate-targets
        expect 0 (success) exit status code
        """
        argv = [
            "kapitan",
            "refs",
            "--validate-targets",
            "--refs-path",
            "examples/kubernetes/refs/targets/",
            "--inventory-path",
            "examples/kubernetes/inventory/",
        ]
        with self.assertRaises(SystemExit) as cm:
            sys.argv = argv
            main()
        argv[0] = BINARY_PATH
        result = subprocess.run(argv, stdout=subprocess.PIPE)
        self.assertEqual(cm.exception.code, result.returncode)

    def test_cli_secret_write_reveal_gkms(self):
        """
        run $ kapitan refs --write gkms:test_secret
        and $ kapitan refs --reveal
        using mock KMS key
        """
        test_secret_content = "mock"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        argv = [
            BINARY_PATH,
            "refs",
            "--write",
            "gkms:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
            "--key",
            "mock",
        ]
        subprocess.run(argv)

        test_tag_content = "revealing: ?{gkms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        argv = [BINARY_PATH, "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        result = subprocess.run(argv, stdout=subprocess.PIPE)
        self.assertEqual("revealing: {}".format(test_secret_content), result.stdout.decode("utf-8"))

        os.remove(test_tag_file)

    def test_cli_secret_write_reveal_awskms(self):
        """
        run $ kapitan refs --write awskms:test_secret
        and $ kapitan refs --reveal
        using mock KMS key
        """
        test_secret_content = "mock"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        argv = [
            BINARY_PATH,
            "refs",
            "--write",
            "awskms:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
            "--key",
            "mock",
        ]
        subprocess.run(argv)

        test_tag_content = "revealing: ?{awskms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        argv = [BINARY_PATH, "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]
        result = subprocess.run(argv, stdout=subprocess.PIPE)
        self.assertEqual("revealing: {}".format(test_secret_content), result.stdout.decode("utf-8"))

        os.remove(test_tag_file)

    def test_cli_secret_write_ref(self):
        """
        run $ kapitan refs --write base64:test_secret
        and $ kapitan refs --reveal -f sometest_file
        """
        test_secret_content = "secret_value!"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        argv = [
            BINARY_PATH,
            "refs",
            "--write",
            "base64:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
        ]
        subprocess.run(argv)
        test_tag_content = "revealing: ?{base64:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        argv = [BINARY_PATH, "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]
        result = subprocess.run(argv, stdout=subprocess.PIPE)
        self.assertEqual("revealing: {}".format(test_secret_content), result.stdout.decode("utf-8"))

        os.remove(test_tag_file)

    def test_cli_secret_write_base64_ref(self):
        """
        run $ kapitan refs --write base64:test_secret --base64
        and $ kapitan refs --reveal -f sometest_file
        """
        test_secret_content = "secret_value!"
        test_secret_content_b64 = base64.b64encode(test_secret_content.encode())
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        argv = [
            BINARY_PATH,
            "refs",
            "--write",
            "base64:test_secret",
            "--base64",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
        ]
        subprocess.run(argv)

        test_tag_content = "revealing: ?{base64:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        argv = [BINARY_PATH, "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        result = subprocess.run(argv, stdout=subprocess.PIPE)
        self.assertEqual(
            "revealing: {}".format(test_secret_content_b64.decode()), result.stdout.decode("utf-8")
        )

        os.remove(test_tag_file)

    def test_cli_secret_subvar_ref(self):
        """
        run $ kapitan refs --write base64:test_secret
        and $ kapitan refs --reveal -f sometest_file
        """
        test_secret_content = """
        var1:
          var2: hello
        var3:
          var4: world
        """
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        argv = [
            BINARY_PATH,
            "refs",
            "--write",
            "base64:test_secret_subvar",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
        ]
        subprocess.run(argv)
        test_tag_content = """
        revealing1: ?{base64:test_secret_subvar@var1.var2}
        revealing2: ?{base64:test_secret_subvar@var3.var4}
        """
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        argv = [BINARY_PATH, "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        result = subprocess.run(argv, stdout=subprocess.PIPE)
        expected = """
        revealing1: {}
        revealing2: {}
        """
        self.assertEqual(expected.format("hello", "world"), result.stdout.decode("utf-8"))
        os.remove(test_tag_file)

    def test_cli_searchvar(self):
        """
        run $ kapitan searchvar mysql.replicas
        """
        argv = [
            "kapitan",
            "searchvar",
            "mysql.replicas",
            "--inventory-path",
            "examples/kubernetes/inventory/",
        ]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            sys.argv = argv
            main()

        argv[0] = BINARY_PATH
        result = subprocess.run(argv, stdout=subprocess.PIPE)

        self.assertEqual(result.stdout.decode("utf-8"), stdout.getvalue())

    def test_cli_inventory(self):
        """
        run $ kapitan inventory -t minikube-es -F -p cluster
        """
        argv = [
            "kapitan",
            "inventory",
            "-t",
            "minikube-es",
            "-F",
            "-p",
            "cluster",
            "--inventory-path",
            "examples/kubernetes/inventory/",
        ]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            sys.argv = argv
            main()
        argv[0] = BINARY_PATH
        result = subprocess.run(argv, stdout=subprocess.PIPE)
        self.assertEqual(result.stdout.decode("utf-8"), stdout.getvalue())

    def tearDown(self):
        shutil.rmtree(REFS_PATH, ignore_errors=True)


@unittest.skipIf(not os.path.exists(BINARY_PATH), "kapitan binary not found")
class TestTerraformCompile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.chdir(os.getcwd() + "/examples/terraform/")

    def test_cli_terraform_compile(self):
        """
        run $kapitan compile
        """
        sys.argv = ["kapitan", "compile"]
        main()
        compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        test_compiled_dir_hash = directory_hash(os.getcwd() + "/../../tests/test_terraform_compiled")
        self.assertEqual(compiled_dir_hash, test_compiled_dir_hash)
        compile_path = tempfile.mkdtemp()
        argv = ["kapitan", "compile"]
        sys.argv = argv
        with contextlib.redirect_stdout(io.StringIO()):
            main()
        argv[0] = "../../" + BINARY_PATH
        argv.extend(["--output-path", compile_path])
        subprocess.run(argv, stdout=subprocess.DEVNULL)
        main_compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        binary_compiled_dir_hash = directory_hash(compile_path + "/compiled")
        self.assertEqual(main_compiled_dir_hash, binary_compiled_dir_hash)

    @classmethod
    def tearDownClass(cls):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


@unittest.skipIf(not os.path.exists(BINARY_PATH), "kapitan binary not found")
class TestKubernetesCompile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.chdir(os.getcwd() + "/examples/kubernetes/")

    def test_cli_kubenetes_compile(self):
        """
        run $kapitan compile
        """
        compile_path = tempfile.mkdtemp()
        argv = ["kapitan", "compile"]
        sys.argv = argv
        with contextlib.redirect_stdout(io.StringIO()):
            main()
        argv[0] = "../../" + BINARY_PATH
        argv.extend(["--output-path", compile_path])
        subprocess.run(argv, stdout=subprocess.DEVNULL)
        main_compiled_dir_hash = directory_hash(os.getcwd() + "/compiled")
        binary_compiled_dir_hash = directory_hash(compile_path + "/compiled")
        self.assertEqual(main_compiled_dir_hash, binary_compiled_dir_hash)

    @classmethod
    def tearDownClass(cls):
        os.chdir(os.getcwd() + "/../../")
        reset_cache()


@unittest.skipIf(not os.path.exists(BINARY_PATH), "kapitan binary not found")
class TestDependencyManager(unittest.TestCase):
    def test_compile_fetch(self):
        temp = tempfile.mkdtemp()
        dir_util.copy_tree("tests/test_resources", temp)
        argv = [
            os.path.join(os.getcwd(), BINARY_PATH),
            "compile",
            "--fetch",
            "--output-path",
            temp,
            "-t",
            "nginx",
            "nginx-dev",
            "monitoring",
            "-p",
            "4",
        ]
        subprocess.run(argv, cwd=temp, stdout=subprocess.DEVNULL)
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "tests")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "acs-engine-autoscaler")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "kapitan-repository")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "components", "source")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "charts", "prometheus")))

    def tearDown(self):
        reset_cache()


@unittest.skipIf(not os.path.exists(BINARY_PATH), "kapitan binary not found")
class TestHelmInputBinary(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join("tests", "test_resources"))

    def test_compile_helm_input(self):
        """compile targets with helm inputs in parallel"""
        temp_main = tempfile.mkdtemp()
        sys.argv = [
            "kapitan",
            "compile",
            "--output-path",
            temp_main,
            "-t",
            "nginx-ingress",
            "nginx-ingress-helm-params",
            "acs-engine-autoscaler",
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            main()
        main_hash = directory_hash(temp_main + "/compiled")

        temp_bin = tempfile.mkdtemp()
        subprocess.run(
            [
                "../../" + BINARY_PATH,
                "compile",
                "--output-path",
                temp_bin,
                "-t",
                "nginx-ingress",
                "nginx-ingress-helm-params",
                "acs-engine-autoscaler",
            ],
            stdout=subprocess.DEVNULL,
        )
        bin_hash = directory_hash(temp_bin + "/compiled")
        self.assertEqual(bin_hash, main_hash)

    @classmethod
    def tearDownClass(cls):
        reset_cache()
        os.chdir("../../")
