# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

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


class HelmBindingUnavailableError(KapitanError):
    """helm input is used when the binding is not available"""

    pass


class HelmTemplateError(KapitanError):
    pass


class GitSubdirNotFoundError(KapitanError):
    """git dependency subdir not found error"""

    pass


class RequestUnsuccessfulError(KapitanError):
    """request error"""

    pass


class KubernetesManifestValidationError(KapitanError):
    """kubernetes manifest schema validation error"""

    pass
