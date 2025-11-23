#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Default configuration values for Kapitan."""

import os


# Kubernetes JSON schema defaults
DEFAULT_KUBERNETES_VERSION: str = "1.14.0"
# standalone is used for standalone json schema (i.e. without external $refs)
# strict is used as it behaves similarly to kubectl
# see https://github.com/garethr/kubernetes-json-schema#kubernetes-json-schemas for more info
SCHEMA_TYPE: str = "standalone-strict"
FILE_PATH_FORMAT: str = f"v{{}}-{SCHEMA_TYPE}/{{}}.json"

# Jinja2 configuration
DEFAULT_JINJA2_FILTERS_PATH: str = os.path.join("lib", "jinja2_filters.py")

# Copier template defaults
COPIER_TEMPLATE_REPOSITORY: str = "https://github.com/kapicorp/kapitan-reference.git"
COPIER_TEMPLATE_REF: str = "copier"
