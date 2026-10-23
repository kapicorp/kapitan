#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Security-focused unit tests for vault_resources without requiring a Vault server."""

import os
import tempfile
import unittest

from kapitan.refs.vault_resources import VaultClient, VaultError


class VaultClientSecurityTest(unittest.TestCase):
    """Test VaultClient security behaviours independent of a running Vault server."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_read_token_from_file_rejects_symlink(self):
        real_file = os.path.join(self.tmpdir, "real_token")
        symlink = os.path.join(self.tmpdir, ".vault-token")

        with open(real_file, "w") as fp:
            fp.write("s3cr3t")

        os.symlink(real_file, symlink)

        client = VaultClient.__new__(VaultClient)
        with self.assertRaises(VaultError) as ctx:
            client.read_token_from_file(symlink)
        self.assertIn("symbolic link", str(ctx.exception))

    def test_read_token_from_file_accepts_regular_file(self):
        token_file = os.path.join(self.tmpdir, ".vault-token")

        with open(token_file, "w") as fp:
            fp.write("s3cr3t")

        client = VaultClient.__new__(VaultClient)
        token = client.read_token_from_file(token_file)
        self.assertEqual(token, "s3cr3t")

    def test_read_token_from_file_rejects_empty_file(self):
        token_file = os.path.join(self.tmpdir, ".vault-token")

        with open(token_file, "w") as fp:
            pass

        client = VaultClient.__new__(VaultClient)
        with self.assertRaises(VaultError) as ctx:
            client.read_token_from_file(token_file)
        self.assertIn("empty", str(ctx.exception))
