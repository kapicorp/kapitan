# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"cli tests"

import base64
import contextlib
import io
import os
import tempfile
import shutil
import subprocess
import sys
import unittest

from kapitan.cli import main

REFS_PATH = tempfile.mkdtemp()

# set GNUPGHOME if only running this test
# otherwise it will reuse the value from test_gpg.py
if os.environ.get("GNUPGHOME", None) is None:
    GNUPGHOME = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = GNUPGHOME


class CliFuncsTest(unittest.TestCase):
    def setUp(self):
        example_key = 'examples/kubernetes/refs/example@kapitan.dev.key'
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

        sys.argv = ["kapitan", "refs", "--write", "gpg:test_secret",
                    "-f", test_secret_file,
                    "--refs-path", REFS_PATH,
                    "--recipients", "example@kapitan.dev"]
        main()

        test_tag_content = "revealing: ?{gpg:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content),
                         stdout.getvalue())

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

        sys.argv = ["kapitan", "refs", "--write", "gpg:test_secretb64",
                    "-f", test_secret_file, "--base64",
                    "--refs-path", REFS_PATH,
                    "--recipients", "example@kapitan.dev"]
        main()

        test_tag_content = "?{gpg:test_secretb64}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        stdout_base64 = base64.b64decode(stdout.getvalue()).decode()
        self.assertEqual(test_secret_content, stdout_base64)

        os.remove(test_tag_file)

    def test_cli_secret_validate_targets(self):
        """
        run $ kapitan refs --validate-targets
        expect 0 (success) exit status code
        """
        with self.assertRaises(SystemExit) as cm:
            sys.argv = ["kapitan", "refs", "--validate-targets",
                        "--refs-path", "examples/kubernetes/refs/targets/",
                        "--inventory-path", "examples/kubernetes/inventory/"]
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

        sys.argv = ["kapitan", "refs", "--write", "gkms:test_secret",
                    "-f", test_secret_file,
                    "--refs-path", REFS_PATH,
                    "--key", "mock"]
        main()

        test_tag_content = "revealing: ?{gkms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content),
                         stdout.getvalue())

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

        sys.argv = ["kapitan", "refs", "--write", "awskms:test_secret",
                    "-f", test_secret_file,
                    "--refs-path", REFS_PATH,
                    "--key", "mock"]
        main()

        test_tag_content = "revealing: ?{awskms:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content),
                         stdout.getvalue())

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

        sys.argv = ["kapitan", "refs", "--write", "plain:test_secret",
                    "-f", test_secret_file,
                    "--refs-path", REFS_PATH]
        main()

        test_tag_content = "revealing: ?{plain:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content),
                         stdout.getvalue())

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

        sys.argv = ["kapitan", "refs", "--write", "base64:test_secret",
                    "-f", test_secret_file,
                    "--refs-path", REFS_PATH]
        main()

        test_tag_content = "revealing: ?{base64:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content),
                         stdout.getvalue())

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

        sys.argv = ["kapitan", "refs", "--write", "base64:test_secret",
                    "--base64", "-f", test_secret_file,
                    "--refs-path", REFS_PATH]
        main()

        test_tag_content = "revealing: ?{base64:test_secret}"
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("revealing: {}".format(test_secret_content_b64.decode()),
                         stdout.getvalue())

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

        sys.argv = ["kapitan", "refs", "--write", "base64:test_secret_subvar",
                    "-f", test_secret_file,
                    "--refs-path", REFS_PATH]
        main()

        test_tag_content = """
        revealing1: ?{base64:test_secret_subvar@var1.var2}
        revealing2: ?{base64:test_secret_subvar@var3.var4}
        """
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()

        expected = """
        revealing1: {}
        revealing2: {}
        """
        self.assertEqual(expected.format("hello", "world"),stdout.getvalue())
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

        sys.argv = ["kapitan", "refs", "--write", "gpg:test_secret_subvar",
                    "-f", test_secret_file,
                    "--refs-path", REFS_PATH,
                    "--recipients", "example@kapitan.dev"]
        main()

        test_tag_content = """
                revealing1: ?{gpg:test_secret_subvar@var1.var2}
                revealing2: ?{gpg:test_secret_subvar@var3.var4}
                """
        test_tag_file = tempfile.mktemp()
        with open(test_tag_file, "w") as fp:
            fp.write(test_tag_content)
        sys.argv = ["kapitan", "refs", "--reveal",
                    "-f", test_tag_file,
                    "--refs-path", REFS_PATH]

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

    def test_cli_searchvar(self):
        """
        run $ kapitan searchvar mysql.replicas
        """
        sys.argv = ["kapitan", "searchvar", "mysql.replicas",
                    "--inventory-path", "examples/kubernetes/inventory/"]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("examples/kubernetes/inventory/targets/minikube-mysql.yml   1\n", stdout.getvalue())

    def test_cli_inventory(self):
        """
        run $ kapitan inventory -t minikube-es -F -p cluster
        """
        sys.argv = ["kapitan", "inventory", "-t", "minikube-es", "-F", "-p", "cluster",
                    "--inventory-path", "examples/kubernetes/inventory/"]

        # set stdout as string
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main()
        self.assertEqual("id: minikube\nname: minikube\ntype: minikube\nuser: minikube\n",
                         stdout.getvalue())

    def tearDown(self):
        shutil.rmtree(REFS_PATH, ignore_errors=True)
