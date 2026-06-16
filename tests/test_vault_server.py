# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for the vault test-server helper."""

import os
import time
import unittest

from tests.vault_server import VaultServer, VaultServerError


class VaultServerTimeoutTest(unittest.TestCase):
    def test_unreachable_vault_addr_raises_instead_of_hanging(self):
        """When VAULT_ADDR points at an unreachable vault, VaultServer must
        give up and raise VaultServerError instead of retrying forever.

        Uses 127.0.0.1:1 (connection refused immediately, no DNS dependency)
        and a short setup timeout so the bounded retry loop trips quickly.
        """
        saved = {
            k: os.environ.get(k)
            for k in ("VAULT_ADDR", "VAULT_TOKEN", "KAPITAN_VAULT_SETUP_TIMEOUT")
        }
        os.environ["VAULT_ADDR"] = "http://127.0.0.1:1"
        os.environ["KAPITAN_VAULT_SETUP_TIMEOUT"] = "3"
        try:
            start = time.monotonic()
            with self.assertRaises(VaultServerError):
                VaultServer()
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 30, "VaultServer hung instead of timing out")
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
