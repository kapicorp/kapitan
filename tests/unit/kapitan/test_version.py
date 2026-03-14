#!/usr/bin/env python3

from packaging.version import Version

from kapitan import version


def test_version_metadata_is_present():
    assert version.PROJECT_NAME == "kapitan"
    assert version.DESCRIPTION
    assert version.AUTHOR
    assert version.AUTHOR_EMAIL
    assert version.LICENCE


def test_version_is_valid():
    Version(version.VERSION)


def test_project_url_looks_valid():
    assert version.URL.startswith("https://")
    assert "github.com" in version.URL
