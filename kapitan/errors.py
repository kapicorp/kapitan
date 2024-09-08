# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"kapitan error classes"


class KapitanError(Exception):
    """generic kapitan error"""


class CompileError(KapitanError):
    """compile error"""


class InventoryError(KapitanError):
    """inventory error"""


class SecretError(KapitanError):
    """secrets error"""


class RefError(KapitanError):
    """ref error"""


class RefBackendError(KapitanError):
    """ref backend error"""


class RefFromFuncError(KapitanError):
    """ref from func error"""


class RefHashMismatchError(KapitanError):
    """ref has mismatch error"""


class HelmBindingUnavailableError(KapitanError):
    """helm input is used when the binding is not available"""


class HelmFetchingError(KapitanError):
    pass


class HelmTemplateError(KapitanError):
    pass


class GitSubdirNotFoundError(KapitanError):
    """git dependency subdir not found error"""


class GitFetchingError(KapitanError):
    """repo not found and/or permission error"""


class RequestUnsuccessfulError(KapitanError):
    """request error"""


class KubernetesManifestValidationError(KapitanError):
    """kubernetes manifest schema validation error"""
