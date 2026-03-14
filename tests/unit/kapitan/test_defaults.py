#!/usr/bin/env python3

import os

from packaging.version import Version

from kapitan import defaults


def test_default_kubernetes_version_is_valid():
    Version(defaults.DEFAULT_KUBERNETES_VERSION)


def test_file_path_format_uses_schema_type():
    expected = f"v1.25.0-{defaults.SCHEMA_TYPE}/deployment.json"
    assert defaults.FILE_PATH_FORMAT.format("1.25.0", "deployment") == expected


def test_default_jinja2_filters_path():
    assert (
        os.path.join("lib", "jinja2_filters.py") == defaults.DEFAULT_JINJA2_FILTERS_PATH
    )


def test_copier_template_defaults_are_set():
    assert defaults.COPIER_TEMPLATE_REPOSITORY.startswith("https://")
    assert defaults.COPIER_TEMPLATE_REF
