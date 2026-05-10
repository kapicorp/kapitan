# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for secret backend error handling (FR-003).

Verifies that each backend:
- Raises its typed *Error on client failure (no raw Exception leaks).
- Does not leak plaintext into log output.
"""

import base64
import logging
import unittest
from unittest.mock import MagicMock, patch


class TestAWSKMSErrorHandling(unittest.TestCase):
    """AWSKMSSecret raises AWSKMSError on client failure."""

    def _make_secret(self):
        from kapitan.refs.secrets.awskms import AWSKMSSecret

        # "mock" key bypasses the real AWS client in _encrypt/_decrypt
        secret = AWSKMSSecret.__new__(AWSKMSSecret)
        secret.data = base64.b64encode(b"mock").decode()
        secret.key = "mock"
        secret.encoding = "original"
        return secret

    def test_decrypt_raises_awskms_error_on_client_failure(self):
        from kapitan.refs.secrets.awskms import AWSKMSError, AWSKMSSecret

        secret = AWSKMSSecret.__new__(AWSKMSSecret)
        # reveal() calls: b64decode(self.data) -> raw bytes -> _decrypt(raw_bytes)
        # _decrypt calls: b64decode(data) -> so self.data must be b64(b64(x))
        raw_cipher = b"rawciphertext"
        secret.data = base64.b64encode(base64.b64encode(raw_cipher)).decode()
        secret.key = "arn:aws:kms:us-east-1:123:key/real"
        secret.encoding = "original"

        boom = RuntimeError("connection refused")
        with patch("kapitan.refs.secrets.awskms.awskms_obj") as mock_obj:
            mock_client = MagicMock()
            mock_client.decrypt.side_effect = boom
            mock_obj.return_value = mock_client

            with self.assertRaises(AWSKMSError) as ctx:
                secret.reveal()

        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)

    def test_encrypt_raises_awskms_error_on_client_failure(self):
        from kapitan.refs.secrets.awskms import AWSKMSError

        boom = RuntimeError("connection refused")
        with patch("kapitan.refs.secrets.awskms.awskms_obj") as mock_obj:
            mock_client = MagicMock()
            mock_client.encrypt.side_effect = boom
            mock_obj.return_value = mock_client

            with self.assertRaises(AWSKMSError) as ctx:
                from kapitan.refs.secrets.awskms import AWSKMSSecret

                AWSKMSSecret("plaintext", "arn:aws:kms:us-east-1:123:key/real")

        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)


class TestGoogleKMSErrorHandling(unittest.TestCase):
    """GoogleKMSSecret raises GoogleKMSError on client failure."""

    def test_decrypt_raises_google_kms_error(self):
        from kapitan.refs.secrets.gkms import GoogleKMSError, GoogleKMSSecret

        secret = GoogleKMSSecret.__new__(GoogleKMSSecret)
        secret.data = base64.b64encode(b"ciphertext").decode()
        secret.key = "projects/p/locations/l/keyRings/r/cryptoKeys/k"
        secret.encoding = "original"

        boom = RuntimeError("API error")
        mock_request = MagicMock()
        mock_request.execute.side_effect = boom

        with patch("kapitan.refs.secrets.gkms.gkms_obj") as mock_obj:
            mock_client = MagicMock()
            mock_client.decrypt.return_value = mock_request
            mock_obj.return_value = mock_client

            with self.assertRaises(GoogleKMSError) as ctx:
                secret.reveal()

        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)

    def test_encrypt_raises_google_kms_error(self):
        from kapitan.refs.secrets.gkms import GoogleKMSError, GoogleKMSSecret

        boom = RuntimeError("quota exceeded")
        mock_request = MagicMock()
        mock_request.execute.side_effect = boom

        with patch("kapitan.refs.secrets.gkms.gkms_obj") as mock_obj:
            mock_client = MagicMock()
            mock_client.encrypt.return_value = mock_request
            mock_obj.return_value = mock_client

            with self.assertRaises(GoogleKMSError) as ctx:
                GoogleKMSSecret(
                    "plaintext", "projects/p/locations/l/keyRings/r/cryptoKeys/k"
                )

        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)


class TestAzureKMSErrorHandling(unittest.TestCase):
    """AzureKMSSecret raises AzureKMSError on client failure."""

    def test_decrypt_raises_azure_kms_error(self):
        from kapitan.refs.secrets.azkms import AzureKMSError, AzureKMSSecret

        secret = AzureKMSSecret.__new__(AzureKMSSecret)
        secret.data = base64.b64encode(b"ciphertext").decode()
        secret.key = "https://vault.azure.net/keys/myKey/abc123"
        secret.encoding = "original"

        boom = RuntimeError("auth failed")
        with patch("kapitan.refs.secrets.azkms.azkms_obj") as mock_obj:
            mock_client = MagicMock()
            mock_client.decrypt.side_effect = boom
            mock_obj.return_value = mock_client

            with self.assertRaises(AzureKMSError) as ctx:
                secret.reveal()

        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)


class TestGPGErrorHandling(unittest.TestCase):
    """GPGSecret raises GPGError when gnupg reports failure."""

    def test_decrypt_raises_gpg_error_on_bad_status(self):
        from kapitan.refs.secrets.gpg import GPGError, GPGSecret

        secret = GPGSecret.__new__(GPGSecret)
        secret.data = base64.b64encode(b"encrypted").decode()
        secret.recipients = [{"fingerprint": "DEADBEEF"}]
        secret.encoding = "original"

        mock_dec = MagicMock()
        mock_dec.ok = False
        mock_dec.status = "decryption failed"

        with patch("kapitan.refs.secrets.gpg.gpg_obj") as mock_obj:
            mock_gpg = MagicMock()
            mock_gpg.decrypt.return_value = mock_dec
            mock_obj.return_value = mock_gpg

            with self.assertRaises(GPGError):
                secret.reveal()


class TestVaultTransitErrorHandling(unittest.TestCase):
    """VaultTransit.reveal raises RefError on corrupt base64 data."""

    def test_reveal_raises_ref_error_on_corrupt_data(self):
        from kapitan.refs.base import RefError
        from kapitan.refs.secrets.vaulttransit import VaultTransit

        secret = VaultTransit.__new__(VaultTransit)
        # Non-alphabet base64 will trigger the b_error path
        secret.data = "not!valid!base64!!!"

        with self.assertRaises(RefError) as ctx:
            secret.reveal()

        self.assertIn("non-alphabet", str(ctx.exception))


class TestModuleLevelCachedImport(unittest.TestCase):
    """No secret backend imports kapitan.cached at module level (FR-003 AC-1)."""

    def test_gpg_no_module_level_cached_import(self):
        import kapitan.refs.secrets.gpg as mod

        self.assertFalse(
            hasattr(mod, "cached"),
            "kapitan.refs.secrets.gpg must not import cached at module level",
        )

    def test_gkms_no_module_level_cached_import(self):
        import kapitan.refs.secrets.gkms as mod

        self.assertFalse(hasattr(mod, "cached"))

    def test_awskms_no_module_level_cached_import(self):
        import kapitan.refs.secrets.awskms as mod

        self.assertFalse(hasattr(mod, "cached"))

    def test_azkms_no_module_level_cached_import(self):
        import kapitan.refs.secrets.azkms as mod

        self.assertFalse(hasattr(mod, "cached"))

    def test_vaultkv_no_module_level_cached_import(self):
        import kapitan.refs.secrets.vaultkv as mod

        self.assertFalse(hasattr(mod, "cached"))

    def test_vaulttransit_no_module_level_cached_import(self):
        import kapitan.refs.secrets.vaulttransit as mod

        self.assertFalse(hasattr(mod, "cached"))


class TestLogRedaction(unittest.TestCase):
    """Secret plaintext must not appear in log output during reveal."""

    def test_base64_reveal_no_plaintext_in_logs(self):
        from kapitan.refs.base64 import Base64Ref

        plaintext = "supersecretpassword123"
        encoded = base64.b64encode(plaintext.encode()).decode()

        ref = Base64Ref.__new__(Base64Ref)
        ref.data = encoded
        ref.encoding = "original"
        ref.embed_refs = False

        log_handler = logging.handlers.MemoryHandler(capacity=1000, flushLevel=100)
        logger = logging.getLogger("kapitan.refs.base64")
        logger.addHandler(log_handler)
        try:
            result = ref.reveal()
            log_handler.flush()
        finally:
            logger.removeHandler(log_handler)

        self.assertEqual(result, plaintext)
        for record in log_handler.buffer:
            self.assertNotIn(plaintext, record.getMessage())


# Need to import logging.handlers after defining the test class
import logging.handlers  # noqa: E402


if __name__ == "__main__":
    unittest.main()
