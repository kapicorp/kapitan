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

"kapitan error classes"


class KapitanError(Exception):
    """generic kapitan error"""
    pass


class CompileError(KapitanError):
    """compile error"""
    pass


class InventoryError(KapitanError):
    """inventory error"""
    pass


class SecretError(KapitanError):
    """secrets error"""
    pass


class RefError(KapitanError):
    """ref error"""
    pass


class RefBackendError(KapitanError):
    """ref backend error"""
    pass


class RefFromFuncError(KapitanError):
    """ref from func error"""
    pass


class RefHashMismatchError(KapitanError):
    """ref has mismatch error"""
    pass


class GitSubdirNotFoundError(KapitanError):
    """git dependency subdir not found error"""
    pass
