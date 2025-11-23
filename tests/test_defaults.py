#!/usr/bin/env python3

# Copyright 2025 The Kapitan Authors
# SPDX-FileCopyrightText: 2025 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the kapitan.defaults module."""

import os

from kapitan import defaults


class TestKubernetesDefaults:
    """Tests for Kubernetes-related default values."""

    def test_default_kubernetes_version_format(self):
        """Test that DEFAULT_KUBERNETES_VERSION is a valid version string."""
        assert isinstance(defaults.DEFAULT_KUBERNETES_VERSION, str)
        assert defaults.DEFAULT_KUBERNETES_VERSION == "1.14.0"
        # Verify it's a valid semantic version format
        parts = defaults.DEFAULT_KUBERNETES_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_schema_type(self):
        """Test that SCHEMA_TYPE is set correctly."""
        assert isinstance(defaults.SCHEMA_TYPE, str)
        assert defaults.SCHEMA_TYPE == "standalone-strict"

    def test_file_path_format(self):
        """Test that FILE_PATH_FORMAT uses correct f-string format."""
        assert isinstance(defaults.FILE_PATH_FORMAT, str)
        # Verify the format string contains the schema type
        assert "standalone-strict" in defaults.FILE_PATH_FORMAT
        # Test that the format string can be used with .format()
        result = defaults.FILE_PATH_FORMAT.format("1.20.0", "deployment")
        assert result == "v1.20.0-standalone-strict/deployment.json"


class TestJinja2Defaults:
    """Tests for Jinja2-related default values."""

    def test_default_jinja2_filters_path(self):
        """Test that DEFAULT_JINJA2_FILTERS_PATH is a valid path."""
        assert isinstance(defaults.DEFAULT_JINJA2_FILTERS_PATH, str)
        expected = os.path.join("lib", "jinja2_filters.py")
        assert defaults.DEFAULT_JINJA2_FILTERS_PATH == expected


class TestCopierDefaults:
    """Tests for Copier template-related default values."""

    def test_copier_template_repository(self):
        """Test that COPIER_TEMPLATE_REPOSITORY is a valid URL."""
        assert isinstance(defaults.COPIER_TEMPLATE_REPOSITORY, str)
        assert defaults.COPIER_TEMPLATE_REPOSITORY.startswith("https://")
        assert "github.com" in defaults.COPIER_TEMPLATE_REPOSITORY
        assert "kapitan-reference" in defaults.COPIER_TEMPLATE_REPOSITORY

    def test_copier_template_ref(self):
        """Test that COPIER_TEMPLATE_REF is set correctly."""
        assert isinstance(defaults.COPIER_TEMPLATE_REF, str)
        assert defaults.COPIER_TEMPLATE_REF == "copier"


class TestModuleStructure:
    """Tests for module-level structure and organization."""

    def test_all_constants_are_strings(self):
        """Test that all exported constants are strings."""
        string_constants = [
            "DEFAULT_KUBERNETES_VERSION",
            "SCHEMA_TYPE",
            "FILE_PATH_FORMAT",
            "DEFAULT_JINJA2_FILTERS_PATH",
            "COPIER_TEMPLATE_REPOSITORY",
            "COPIER_TEMPLATE_REF",
        ]
        for const_name in string_constants:
            value = getattr(defaults, const_name)
            assert isinstance(value, str), f"{const_name} should be a string"

    def test_no_runtime_dependencies(self):
        """Test that defaults module has no runtime side effects."""
        # This test verifies the module can be imported without side effects
        # Just importing the module should not raise any exceptions
        import importlib

        importlib.reload(defaults)
