# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

import kapitan.utils as utils_package


def test_package_exports_resolve_expected_symbols():
    assert utils_package.compare_versions("1.2.3", "1.2.3") == "equal"
    assert utils_package.sha256_string("kapitan") == utils_package.sha256_string(
        "kapitan"
    )
    assert callable(utils_package.render_jinja2_file)


def test_package_dir_includes_public_exports():
    entries = dir(utils_package)
    assert "compare_versions" in entries
    assert "render_jinja2_file" in entries


def test_package_missing_attr_raises_attribute_error():
    with pytest.raises(AttributeError):
        _ = utils_package.not_a_real_attr
