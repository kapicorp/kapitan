# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"cli tests"

import base64
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from kapitan.cli import main
from kapitan.refs.secrets import vaultkv

REFS_PATH = tempfile.mkdtemp()

# set GNUPGHOME if only running this test
# otherwise it will reuse the value from test_gpg.py
if os.environ.get("GNUPGHOME", None) is None:
    GNUPGHOME = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = GNUPGHOME


class CliFuncsTest(unittest.TestCase):
    def setUp(self):
        example_key = "examples/kubernetes/refs/example@kapitan.dev.key"
        example_key = os.path.join(os.getcwd(), example_key)
        example_key_ownertrust = tempfile.mktemp()

        # always trust this key - for testing only!
        with open(example_key_ownertrust, "w") as fp:
            fp.write("D9234C61F58BEB3ED8552A57E28DC07A3CBFAE7C:6\n")

        subprocess.run(["gpg", "--import", example_key])
        subprocess.run(["gpg", "--import-ownertrust", example_key_ownertrust])
        os.remove(example_key_ownertrust)

    def test_cli_secret_write_reveal_gpg(self):
        """
        run $ kapitan refs --write gpg:test_secret
        and $ kapitan refs --reveal
        with example@kapitan.dev recipient
        """
        test_secret_content = "I am a secret!"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "gpg:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
            "--recipients",
            "example@kapitan.dev",
        ]
        main()

        test_tag_content = "revealing: ?{gpg:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content), stdout.getvalue())

        os.remove(test_tag_file)

    def test_cli_secret_base64_write_reveal_gpg(self):
        """
        run $ kapitan refs --write gpg:test_secretb64 --base64
        and $ kapitan refs --reveal
        with example@kapitan.dev recipient
        """
        test_secret_content = "I am another secret!"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "gpg:test_secretb64",
            "-f",
            test_secret_file,
            "--base64",
            "--refs-path",
            REFS_PATH,
            "--recipients",
            "example@kapitan.dev",
        ]
        main()

        test_tag_content = "?{gpg:test_secretb64}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        stdout_base64 = base64.b64decode(stdout.getvalue()).decode()
        self.assertEqual(test_secret_content, stdout_base64)

        os.remove(test_tag_file)

    def test_cli_ref_reveal_recursive_dir(self):
        """
        run $ kapitan refs --reveal -f /some/dir
        where /some/dir has manifests in nested dirs:
        /some/dir/1.yml
        /some/dir/another/2.yml
        /some/dir/another/dir/3.yml
        """
        # create 3 refs
        for ref_count in range(1, 4):
            ref_content = "I am ref{}!".format(ref_count)
            ref_file = tempfile.mktemp()
            with open(ref_file, "w") as fp:
                fp.write(ref_content)

            sys.argv = [
                "kapitan",
                "refs",
                "--write",
                "base64:test_ref_{}".format(ref_count),
                "-f",
                ref_file,
                "--refs-path",
                REFS_PATH,
            ]
            main()

        # create nested dir structure with unrevealed manifests
        unrevealed_dir = tempfile.mkdtemp()
        ref_content = """---\nref_value_{}: {}\n"""

        some_dir = os.path.join(unrevealed_dir, "some/dir")
        some_dir_other = os.path.join(unrevealed_dir, "some/dir/another")
        some_dir_another = os.path.join(unrevealed_dir, "some/dir/another/dir")
        os.makedirs(some_dir)
        os.makedirs(some_dir_other)
        os.makedirs(some_dir_another)

        # write manifests in nested dirs
        expected_output = ""
        for dir_path in enumerate((some_dir, some_dir_other, some_dir_another), 1):
            count, path = dir_path
            manifest_path = os.path.join(path, "{}.yml".format(count))
            with open(manifest_path, "w") as f:
                ref = "?{{base64:test_ref_{}}}".format(count)
                f.write(ref_content.format(count, ref))

            # set expected revealed output
            expected_ref_rev = "I am ref{}!".format(count)
            expected_output += ref_content.format(count, expected_ref_rev)

        sys.argv = ["kapitan", "refs", "--reveal", "-f", some_dir, "--refs-path", REFS_PATH]
        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual(expected_output, stdout.getvalue())

    def test_cli_secret_validate_targets(self):
        """
        run $ kapitan refs --validate-targets
        expect 0 (success) exit status code
        """
        with self.assertRaises(SystemExit) as cm:
            sys.argv = [
                "kapitan",
                "refs",
                "--validate-targets",
                "--refs-path",
                "examples/kubernetes/refs/targets/",
                "--inventory-path",
                "examples/kubernetes/inventory/",
            ]
            main()
        self.assertEqual(cm.exception.code, 0)

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

        sys.argv = [
            "kapitan",
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
        main()

        test_tag_content = "revealing: ?{gkms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content), stdout.getvalue())

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

        sys.argv = [
            "kapitan",
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
        main()

        test_tag_content = "revealing: ?{awskms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content), stdout.getvalue())

        os.remove(test_tag_file)

    def test_cli_secret_write_plain_ref(self):
        """
        run $ kapitan refs --write plain:test_secret
        and $ kapitan refs --reveal -f sometest_file
        """
        test_secret_content = "secret_value!"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "plain:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
        ]
        main()

        test_tag_content = "revealing: ?{plain:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content), stdout.getvalue())

        os.remove(test_tag_file)

    def test_cli_secret_write_base64_ref(self):
        """
        run $ kapitan refs --write base64:test_secret
        and $ kapitan refs --reveal -f sometest_file
        """
        test_secret_content = "secret_value!"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "base64:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
        ]
        main()

        test_tag_content = "revealing: ?{base64:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content), stdout.getvalue())

        os.remove(test_tag_file)

    def test_cli_secret_write_base64_encoded_ref(self):
        """
        run $ kapitan refs --write base64:test_secret --base64
        and $ kapitan refs --reveal -f sometest_file
        """
        test_secret_content = "secret_value!"
        test_secret_content_b64 = base64.b64encode(test_secret_content.encode())
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "base64:test_secret",
            "--base64",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
        ]
        main()

        test_tag_content = "revealing: ?{base64:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content_b64.decode()), stdout.getvalue())

        os.remove(test_tag_file)

    def test_cli_secret_subvar_base64_ref(self):
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

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "base64:test_secret_subvar",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
        ]
        main()

        test_tag_content = """
        revealing1: ?{base64:test_secret_subvar@var1.var2}
        revealing2: ?{base64:test_secret_subvar@var3.var4}
        """
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()

        expected = """
        revealing1: {}
        revealing2: {}
        """
        self.assertEqual(expected.format("hello", "world"), stdout.getvalue())
        os.remove(test_tag_file)

    def test_cli_secret_subvar_gpg(self):
        """
        run $ kapitan refs --write gpg:test_secret
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

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "gpg:test_secret_subvar",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
            "--recipients",
            "example@kapitan.dev",
        ]
        main()

        test_tag_content = """
                revealing1: ?{gpg:test_secret_subvar@var1.var2}
                revealing2: ?{gpg:test_secret_subvar@var3.var4}
                """
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()

        expected = """
                revealing1: {}
                revealing2: {}
                """
        self.assertEqual(expected.format("hello", "world"), stdout.getvalue())
        os.remove(test_tag_file)

    @patch.object(vaultkv.VaultSecret, "_decrypt")
    def test_cli_secret_write_vault(self, mock_reveal):
        """
        run $ kapitan refs --write vaultkv:test_secret
        and $ kapitan refs --reveal -f sometest_file
        """
        test_secret_content = "foo:secret_test_key"
        test_secret_content_value = "secret_value"
        test_secret_file = tempfile.mktemp()
        with open(test_secret_file, "w") as fp:
            fp.write(test_secret_content)

        sys.argv = [
            "kapitan",
            "refs",
            "--write",
            "vaultkv:test_secret",
            "-f",
            test_secret_file,
            "--refs-path",
            REFS_PATH,
            "--vault-auth",
            "token",
        ]
        main()

        test_tag_content = "revealing: ?{vaultkv:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)

        mock_reveal.return_value = test_secret_content_value
        sys.argv = ["kapitan", "refs", "--reveal", "-f", test_tag_file, "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {value}".format(value=test_secret_content_value), stdout.getvalue())

        os.remove(test_tag_file)

    def test_cli_searchvar(self):
        """
        run $ kapitan searchvar mysql.replicas
        """
        sys.argv = [
            "kapitan",
            "searchvar",
            "mysql.replicas",
            "--inventory-path",
            "examples/kubernetes/inventory/",
        ]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("examples/kubernetes/inventory/targets/minikube-mysql.yml   1\n", stdout.getvalue())

    def test_cli_inventory(self):
        """
        run $ kapitan inventory -t minikube-es -F -p cluster
        """
        sys.argv = [
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
            main()
        self.assertEqual("id: minikube\nname: minikube\ntype: minikube\nuser: minikube\n", stdout.getvalue())

    def tearDown(self):
        shutil.rmtree(REFS_PATH, ignore_errors=True)
