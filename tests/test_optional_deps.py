#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for MissingOptionalDependencyError raised when optional extras are absent."""

import sys
import unittest
from contextlib import contextmanager

from kapitan.errors import MissingOptionalDependencyError


@contextmanager
def _absent_modules(*names: str):
    """Temporarily make *names* appear absent from sys.modules.

    Saves any existing entries, sets them to None (which makes 'import foo'
    raise ImportError), then restores the original state on exit.
    """
    saved = {n: sys.modules.pop(n) for n in names if n in sys.modules}
    for name in names:
        sys.modules[name] = None
    try:
        yield
    finally:
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(saved)


class TestMissingInventoryBackends(unittest.TestCase):
    """Backend-discovery tests: simulate each missing optional dep via sys.modules injection."""

    def _load_reclass_rs(self):
        # Re-import the loader fresh each time to avoid cached module state.
        from kapitan.inventory import load_reclass_rs_backend

        return load_reclass_rs_backend

    def _load_omegaconf(self):
        from kapitan.inventory import load_omegaconf_backend

        return load_omegaconf_backend

    def test_reclass_rs_missing_raises_typed_error(self):
        """load_reclass_rs_backend() raises MissingOptionalDependencyError when reclass_rs absent."""
        loader = self._load_reclass_rs()
        with _absent_modules("reclass_rs", "kapitan.inventory.backends.reclass_rs"):
            with self.assertRaises(MissingOptionalDependencyError) as ctx:
                loader()
        err = ctx.exception
        self.assertIn("reclass-rs", err.extra)
        # Message must name the install extra so users know what to run.
        self.assertIn("reclass-rs", str(err))
        self.assertIn("pip install", str(err))

    def test_reclass_rs_missing_error_attributes(self):
        """MissingOptionalDependencyError for reclass-rs has correct feature and extra attrs."""
        loader = self._load_reclass_rs()
        with _absent_modules("reclass_rs", "kapitan.inventory.backends.reclass_rs"):
            with self.assertRaises(MissingOptionalDependencyError) as ctx:
                loader()
        err = ctx.exception
        self.assertEqual(err.extra, "reclass-rs")
        self.assertIn("reclass-rs", err.feature)

    def test_omegaconf_missing_raises_typed_error(self):
        """load_omegaconf_backend() raises MissingOptionalDependencyError when omegaconf absent."""
        loader = self._load_omegaconf()
        with _absent_modules(
            "omegaconf",
            "kapitan.inventory.backends.omegaconf",
            "kapitan.inventory.backends.omegaconf.migrate",
            "kapitan.inventory.backends.omegaconf.resolvers",
        ):
            with self.assertRaises(MissingOptionalDependencyError) as ctx:
                loader()
        err = ctx.exception
        self.assertIn("omegaconf", err.extra)
        self.assertIn("omegaconf", str(err))
        self.assertIn("pip install", str(err))

    def test_omegaconf_missing_error_attributes(self):
        """MissingOptionalDependencyError for omegaconf has correct feature and extra attrs."""
        loader = self._load_omegaconf()
        with _absent_modules(
            "omegaconf",
            "kapitan.inventory.backends.omegaconf",
            "kapitan.inventory.backends.omegaconf.migrate",
            "kapitan.inventory.backends.omegaconf.resolvers",
        ):
            with self.assertRaises(MissingOptionalDependencyError) as ctx:
                loader()
        err = ctx.exception
        self.assertEqual(err.extra, "omegaconf")
        self.assertIn("omegaconf", err.feature)

    def test_reclass_backend_available_without_optional_deps(self):
        """Reclass (mandatory) backend loads fine regardless of optional dep availability."""
        from kapitan.inventory import load_reclass_backend

        with _absent_modules("reclass_rs", "omegaconf"):
            result = load_reclass_backend()
        self.assertIsNotNone(result)


class TestMissingJsonnetRuntimes(unittest.TestCase):
    """Input-runtime tests: simulate missing jsonnet/gojsonnet via sys.modules injection."""

    def _get_selector(self):
        from kapitan.inputs.jsonnet import select_jsonnet_runtime

        return select_jsonnet_runtime

    def test_gojsonnet_missing_raises_typed_error(self):
        """select_jsonnet_runtime(use_go=True) raises MissingOptionalDependencyError when absent."""
        selector = self._get_selector()
        with _absent_modules("_gojsonnet"):
            with self.assertRaises(MissingOptionalDependencyError) as ctx:
                selector(use_go=True)
        err = ctx.exception
        self.assertEqual(err.extra, "gojsonnet")
        self.assertIn("pip install", str(err))

    def test_jsonnet_missing_raises_typed_error(self):
        """select_jsonnet_runtime(use_go=False) raises MissingOptionalDependencyError when absent."""
        selector = self._get_selector()
        with _absent_modules("_jsonnet"):
            with self.assertRaises(MissingOptionalDependencyError) as ctx:
                selector(use_go=False)
        err = ctx.exception
        self.assertEqual(err.extra, "jsonnet")
        self.assertIn("pip install", str(err))

    def test_missing_error_is_subclass_of_kapitan_error(self):
        """MissingOptionalDependencyError is a KapitanError for consistent error handling."""
        from kapitan.errors import KapitanError

        err = MissingOptionalDependencyError("some feature", "some-extra")
        self.assertIsInstance(err, KapitanError)

    def test_error_message_format(self):
        """Error message includes feature name, extra name, and install command."""
        err = MissingOptionalDependencyError("Go Jsonnet runtime", "gojsonnet")
        msg = str(err)
        self.assertIn("Go Jsonnet runtime", msg)
        self.assertIn("gojsonnet", msg)
        self.assertIn("pip install", msg)
        self.assertIn("kapitan[gojsonnet]", msg)


if __name__ == "__main__":
    unittest.main()
