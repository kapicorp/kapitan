import os
import tempfile
import unittest

import yaml

from kapitan.cached import reset_cache
from kapitan.inventory import InventoryBackends
from kapitan.utils import from_dot_kapitan


class FromDotKapitanTest(unittest.TestCase):
    "Test loading flags from .kapitan"

    def _setup_dot_kapitan(self, config):
        with open(self.work_dir.name + "/.kapitan", "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f)

    def setUp(self):
        self.orig_dir = os.getcwd()
        self.work_dir = tempfile.TemporaryDirectory()
        os.chdir(self.work_dir.name)

    def test_no_file(self):
        assert from_dot_kapitan("compile", "inventory-path", "./some/fallback") == "./some/fallback"

    def test_no_option(self):
        self._setup_dot_kapitan(
            {
                "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert from_dot_kapitan("inventory", "inventory-path", "./some/fallback") == "./some/fallback"

    def test_cmd_option(self):
        self._setup_dot_kapitan(
            {
                "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert from_dot_kapitan("compile", "inventory-path", "./some/fallback") == "./path/to/inv"

    def test_global_option(self):
        self._setup_dot_kapitan(
            {"global": {"inventory-path": "./some/path"}, "compile": {"inventory-path": "./path/to/inv"}}
        )
        assert from_dot_kapitan("inventory", "inventory-path", "./some/fallback") == "./some/path"

    def test_command_over_global_option(self):
        self._setup_dot_kapitan(
            {"global": {"inventory-path": "./some/path"}, "compile": {"inventory-path": "./path/to/inv"}}
        )
        assert from_dot_kapitan("compile", "inventory-path", "./some/fallback") == "./path/to/inv"

    def tearDown(self):
        self.work_dir.cleanup()
        os.chdir(self.orig_dir)
        reset_cache()
