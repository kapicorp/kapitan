#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"default values for kapitan variables"

import os

DEFAULT_KUBERNETES_VERSION = "1.14.0"
# standalone is used for standalone json schema (i.e. without external $refs)
# strict is used as it behaves similarly to kubectl
# see https://github.com/garethr/kubernetes-json-schema#kubernetes-json-schemas for more info
SCHEMA_TYPE = "standalone-strict"
FILE_PATH_FORMAT = "v{}-%s/{}.json" % SCHEMA_TYPE

# default path from where user defined custom filters are read
DEFAULT_JINJA2_FILTERS_PATH = os.path.join("lib", "jinja2_filters.py")
