#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Project description variables."""

from importlib.metadata import PackageNotFoundError, version


PROJECT_NAME = "kapitan"
DESCRIPTION = "Generic templated configuration management for Kubernetes, Terraform and other things"
AUTHOR = "Ricardo Amaro"
AUTHOR_EMAIL = "ramaro@kapicorp.com"
LICENCE = "Apache License 2.0"
URL = "https://github.com/kapicorp/kapitan"

# When running from an installed package (wheel, sdist), use the version
# computed by the build backend (uv-dynamic-versioning). When running from
# source without installation, fall back to the static version.
try:
    VERSION = version("kapitan")
except PackageNotFoundError:
    VERSION = "0.36.0"
