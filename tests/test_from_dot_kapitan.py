import os
import tempfile
import unittest

import pytest
import yaml

from kapitan.cached import reset_cache
from kapitan.cli import build_parser
from kapitan.inventory import InventoryBackends
from kapitan.utils import from_dot_kapitan, warn_unknown_dot_kapitan_keys


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
        assert (
            from_dot_kapitan("compile", "inventory-path", "./some/fallback")
            == "./some/fallback"
        )

    def test_no_option(self):
        self._setup_dot_kapitan(
            {
                "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert (
            from_dot_kapitan("inventory", "inventory-path", "./some/fallback")
            == "./some/fallback"
        )

    def test_cmd_option(self):
        self._setup_dot_kapitan(
            {
                "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert (
            from_dot_kapitan("compile", "inventory-path", "./some/fallback")
            == "./path/to/inv"
        )

    def test_global_option(self):
        self._setup_dot_kapitan(
            {
                "global": {"inventory-path": "./some/path"},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert (
            from_dot_kapitan("inventory", "inventory-path", "./some/fallback")
            == "./some/path"
        )

    def test_command_over_global_option(self):
        self._setup_dot_kapitan(
            {
                "global": {"inventory-path": "./some/path"},
                "compile": {"inventory-path": "./path/to/inv"},
            }
        )
        assert (
            from_dot_kapitan("compile", "inventory-path", "./some/fallback")
            == "./path/to/inv"
        )

    def tearDown(self):
        self.work_dir.cleanup()
        os.chdir(self.orig_dir)
        reset_cache()


@pytest.fixture
def dot_kapitan(tmp_path, monkeypatch):
    """Write a .kapitan into a fresh cwd and build the parser, which reads it."""

    def write(config):
        (tmp_path / ".kapitan").write_text(yaml.safe_dump(config))
        build_parser()

    monkeypatch.chdir(tmp_path)
    reset_cache()
    yield write
    reset_cache()


def test_unknown_dot_kapitan_keys_are_reported(dot_kapitan, caplog):
    dot_kapitan(
        {
            "inventory_backend": {"omegaconf": True},
            "compile": {"inventory_path": "./inv"},
            "compiel": {"indent": 4},
        }
    )

    warn_unknown_dot_kapitan_keys()

    warnings = {r.getMessage() for r in caplog.records if r.levelname == "WARNING"}
    assert warnings == {
        ".kapitan: ignoring unknown key 'omegaconf' in section 'inventory_backend'",
        ".kapitan: ignoring unknown key 'inventory_path' in section 'compile', "
        "did you mean 'inventory-path'?",
        ".kapitan: ignoring unknown section 'compiel', did you mean 'compile'?",
    }


def test_known_dot_kapitan_keys_are_not_reported(dot_kapitan, caplog):
    dot_kapitan(
        {
            "version": "0.36",
            "global": {"inventory-path": "./inv", "indent": 4},
            "compile": {"parallelism": 2},
            "inventory_backend": {"inventory-backend": "omegaconf"},
        }
    )

    warn_unknown_dot_kapitan_keys()

    assert not [r for r in caplog.records if r.levelname == "WARNING"]
