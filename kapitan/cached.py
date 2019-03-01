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

"cached module"

inv = {}
inv_cache = {}
gpg_obj = None
gkms_obj = None
awskms_obj = None
dot_kapitan = {}

def reset_cache():
    global inv, inv_cache, gpg_obj, gkms_obj, awskms_obj, dot_kapitan
    inv = {}
    inv_cache = {}
    gpg_obj = None
    gkms_obj = None
    awskms_obj = None
    dot_kapitan = {}
