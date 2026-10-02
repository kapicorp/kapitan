#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for generator schema discovery and validation."""

import importlib.util
import json
import logging
import tempfile
import unittest
from pathlib import Path

import pytest
import yaml

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan
from kapitan.dependency_manager.schema_validation import (
    SourceTrackerCache,
    _resolve_schema_path,
    validate_generator_schemas,
)
from kapitan.inventory import InventoryBackends
from kapitan.inventory.model import KapitanInventorySettings
from kapitan.inventory.model.dependencies import KapitanDependencyGitConfig


# Backends to exercise in end-to-end compile tests. Optional backends are
# skipped at runtime when their module is not installed.
INVENTORY_BACKENDS = [
    InventoryBackends.RECLASS,
    InventoryBackends.RECLASS_RS,
    InventoryBackends.OMEGACONF,
]


def _skip_if_backend_unavailable(backend):
    module_name = backend.replace("-", "_")
    if not importlib.util.find_spec(module_name):
        pytest.skip(f"backend module {module_name} not available")


class GeneratorSchemaValidationTest(unittest.TestCase):
    """Unit tests for generator schema discovery and validation."""

    def _make_dep(self, output_path, schema_path=None, schema_inventory_path=None):
        return KapitanDependencyGitConfig(
            type="git",
            source="https://example.com/repo.git",
            output_path=output_path,
            schema_path=schema_path,
            schema_inventory_path=schema_inventory_path,
        )

    def test_schema_discovery_default_path(self):
        """When schema_path is not set, discover <output_path>/schema.json."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)
            schema_file = output_dir / "schema.json"
            schema_file.write_text(json.dumps({"type": "object"}))

            dep = self._make_dep(output_path=str(output_dir))

            result = _resolve_schema_path(dep)
            self.assertEqual(result, schema_file)

    def test_schema_discovery_explicit_path(self):
        """When schema_path is set, it overrides the default location."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)
            custom_schema = Path(tmp) / "custom" / "schema.json"
            custom_schema.parent.mkdir(parents=True)
            custom_schema.write_text(json.dumps({"type": "object"}))

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_path=str(custom_schema),
            )

            result = _resolve_schema_path(dep)
            self.assertEqual(result, custom_schema)

    def test_missing_schema_returns_none(self):
        """When no schema file exists, _resolve_schema_path returns None."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)

            dep = self._make_dep(output_path=str(output_dir))

            result = _resolve_schema_path(dep)
            self.assertIsNone(result)

    def test_validation_warn(self):
        """Schema mismatches return findings with error details."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)
            schema = {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "syncPolicy": {
                        "type": "object",
                        "properties": {
                            "automated": {"type": "boolean"},
                        },
                    },
                },
            }
            (output_dir / "schema.json").write_text(json.dumps(schema))

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_inventory_path="parameters.components.argocd",
            )
            parameters = {
                "parameters": {
                    "components": {
                        "argocd": {
                            "namespace": "argocd",
                            "syncPolicy": {
                                "automated": "true",
                            },
                        },
                    },
                },
            }

            target_obj = KapitanInventorySettings(dependencies=[dep])
            findings = validate_generator_schemas(target_obj, parameters, str(tmp))

            self.assertEqual(len(findings), 1)
            self.assertIn("boolean", findings[0]["errors"][0]["message"])

    def test_validation_error_mode(self):
        """validate_generator_schemas returns findings regardless of mode."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)
            schema = {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                },
            }
            (output_dir / "schema.json").write_text(json.dumps(schema))

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_inventory_path="parameters.data",
            )
            parameters = {
                "parameters": {
                    "data": {"count": "not-an-int"},
                },
            }

            target_obj = KapitanInventorySettings(dependencies=[dep])
            findings = validate_generator_schemas(target_obj, parameters, str(tmp))
            self.assertEqual(len(findings), 1)
            self.assertIn("not-an-int", findings[0]["errors"][0]["message"])

    def test_validation_disabled(self):
        """validate_generator_schemas still returns findings when called directly."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)
            schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
            (output_dir / "schema.json").write_text(json.dumps(schema))

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_inventory_path="parameters.data",
            )
            parameters = {"parameters": {"data": {"x": "bad"}}}

            target_obj = KapitanInventorySettings(dependencies=[dep])
            findings = validate_generator_schemas(target_obj, parameters, str(tmp))
            self.assertEqual(len(findings), 1)

    def test_missing_schema_skips_validation(self):
        """Missing schema files produce no findings."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_inventory_path="parameters.components.argocd",
            )
            parameters = {
                "parameters": {
                    "components": {
                        "argocd": {"namespace": "argocd"},
                    },
                },
            }

            target_obj = KapitanInventorySettings(dependencies=[dep])
            findings = validate_generator_schemas(target_obj, parameters, str(tmp))
            self.assertEqual(len(findings), 0)

    def test_validation_source_location(self):
        """When inventory files are present, the formatted error includes source location."""
        with tempfile.TemporaryDirectory() as tmp:
            inv_dir = Path(tmp) / "inventory"
            classes_dir = inv_dir / "classes"
            classes_dir.mkdir(parents=True)

            # Write a class that defines the violating value.
            class_file = classes_dir / "argocd.yml"
            class_file.write_text(
                "parameters:\n"
                "  components:\n"
                "    argocd:\n"
                "      syncPolicy:\n"
                '        automated: "true"\n'
            )

            output_dir = Path(tmp) / "lib" / "argocd"
            output_dir.mkdir(parents=True)
            schema = {
                "type": "object",
                "properties": {
                    "syncPolicy": {
                        "type": "object",
                        "properties": {
                            "automated": {"type": "boolean"},
                        },
                    },
                },
            }
            (output_dir / "schema.json").write_text(json.dumps(schema))

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_inventory_path="parameters.components.argocd",
            )
            parameters = {
                "parameters": {
                    "components": {
                        "argocd": {
                            "syncPolicy": {
                                "automated": "true",
                            },
                        },
                    },
                },
            }

            target_obj = KapitanInventorySettings(dependencies=[dep])
            findings = validate_generator_schemas(target_obj, parameters, str(inv_dir))

            self.assertEqual(len(findings), 1)
            formatted = findings[0]["errors"][0]["formatted"]
            # Should contain the source file path and line context.
            self.assertIn(str(class_file), formatted)
            self.assertIn("automated:", formatted)
            self.assertIn("E-argocd.type", formatted)

    def test_validation_multiple_errors(self):
        """A schema mismatch against multiple constraints reports every error."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "testgen"
            output_dir.mkdir(parents=True)
            schema = {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "name": {"type": "string"},
                },
            }
            (output_dir / "schema.json").write_text(json.dumps(schema))

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_inventory_path="parameters.components.testgen",
            )
            parameters = {
                "parameters": {
                    "components": {
                        "testgen": {
                            "count": "not-an-int",
                            "name": 123,
                        },
                    },
                },
            }

            target_obj = KapitanInventorySettings(dependencies=[dep])
            findings = validate_generator_schemas(target_obj, parameters, str(tmp))

            self.assertEqual(len(findings), 1)
            self.assertEqual(len(findings[0]["errors"]), 2)

    def test_validation_missing_inventory_path_warns(self):
        """When a schema exists but the configured inventory path is missing, a warning is logged."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "lib" / "testgen"
            output_dir.mkdir(parents=True)
            (output_dir / "schema.json").write_text(json.dumps({"type": "object"}))

            dep = self._make_dep(
                output_path=str(output_dir),
                schema_inventory_path="parameters.does.not.exist",
            )
            parameters = {"parameters": {"components": {"testgen": {}}}}

            target_obj = KapitanInventorySettings(dependencies=[dep])
            with self.assertLogs(level=logging.WARNING) as cm:
                findings = validate_generator_schemas(target_obj, parameters, str(tmp))

            self.assertEqual(len(findings), 0)
            self.assertTrue(
                any("does not resolve" in msg for msg in cm.output),
                f"Expected warning about missing inventory path, got: {cm.output}",
            )

    def test_source_tracker_cache_reuses_instances(self):
        """SourceTrackerCache returns the same tracker for repeated lookups."""
        with tempfile.TemporaryDirectory() as tmp:
            yaml_file = Path(tmp) / "test.yml"
            yaml_file.write_text("foo: bar\n")

            cache = SourceTrackerCache()
            tracker1 = cache.get(yaml_file)
            tracker2 = cache.get(yaml_file)

            self.assertIs(tracker1, tracker2)


class TestGeneratorSchemaValidationCompile:
    """End-to-end compile tests for generator schema validation."""

    @pytest.fixture
    def schema_validation_inventory(self, temp_dir):
        """Create an isolated inventory for schema validation compile tests."""
        inv_dir = Path(temp_dir) / "inventory"
        targets_dir = inv_dir / "targets"
        classes_dir = inv_dir / "classes"
        targets_dir.mkdir(parents=True)
        classes_dir.mkdir(parents=True)

        common = {"parameters": {"kapitan": {"compile": []}}}
        (classes_dir / "common.yml").write_text(yaml.dump(common))

        # Create schema for dependency
        schema_dir = Path(temp_dir) / "lib" / "testgen"
        schema_dir.mkdir(parents=True)
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        (schema_dir / "schema.json").write_text(json.dumps(schema))

        # Create a dummy file for copy input so compile_target writes output
        (Path(temp_dir) / "dummy.txt").write_text("hello")

        return temp_dir

    def _write_target(self, base_dir, mode):
        target = {
            "classes": ["common"],
            "parameters": {
                "kapitan": {
                    "vars": {
                        "target": "test",
                    },
                    "compile": [
                        {
                            "output_path": ".",
                            "input_type": "copy",
                            "input_paths": ["dummy.txt"],
                        }
                    ],
                    "generator_schema_validation": mode,
                    "dependencies": [
                        {
                            "type": "git",
                            "source": "https://example.com/repo.git",
                            "output_path": "lib/testgen",
                            "schema_inventory_path": "parameters.components.testgen",
                        }
                    ],
                },
                "components": {
                    "testgen": {
                        "count": "not-an-int",
                    }
                },
            },
        }
        targets_dir = Path(base_dir) / "inventory" / "targets"
        (targets_dir / "test.yml").write_text(yaml.dump(target))

    @pytest.mark.parametrize("backend", INVENTORY_BACKENDS)
    def test_compile_error_mode_raises(
        self, schema_validation_inventory, monkeypatch, backend
    ):
        """With generator_schema_validation: error, compile exits with failure."""
        _skip_if_backend_unavailable(backend)
        self._write_target(schema_validation_inventory, "error")
        monkeypatch.chdir(schema_validation_inventory)
        reset_cache()
        with pytest.raises(SystemExit) as exc_info:
            kapitan("compile", "-t", "test", "--inventory-backend", backend)
        assert exc_info.value.code == 1
        reset_cache()

    @pytest.mark.parametrize("backend", INVENTORY_BACKENDS)
    def test_compile_warn_mode_succeeds(
        self, schema_validation_inventory, monkeypatch, backend
    ):
        """With generator_schema_validation: warn, compile succeeds despite mismatch."""
        _skip_if_backend_unavailable(backend)
        self._write_target(schema_validation_inventory, "warn")
        monkeypatch.chdir(schema_validation_inventory)
        reset_cache()
        kapitan("compile", "-t", "test", "--inventory-backend", backend)
        reset_cache()
