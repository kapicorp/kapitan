#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
