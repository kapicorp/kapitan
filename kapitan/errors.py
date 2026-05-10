# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"kapitan error classes"


class KapitanError(Exception):
    """Generic Kapitan error; base class for the entire hierarchy."""

    def to_dict(self):
        """Return a JSON-serialisable dict representation of this error."""
        result = {"error": type(self).__name__, "message": str(self)}
        for key, value in vars(self).items():
            if not key.startswith("_"):
                result[key] = value
        return result


# ---------------------------------------------------------------------------
# Branch classes
# ---------------------------------------------------------------------------


class UserError(KapitanError):
    """Errors caused by user-facing configuration or inventory mistakes."""


class BackendError(KapitanError):
    """Errors from external backends: secrets stores, inventory backends, helm, cuelang."""


class InternalError(KapitanError):
    """Errors indicating bugs or unexpected internal state in Kapitan."""


# ---------------------------------------------------------------------------
# UserError branch
# ---------------------------------------------------------------------------


class CompileError(UserError):
    """Raised when a compilation step fails."""

    def __init__(self, message="", *, target_name=None, source_path=None):
        super().__init__(message)
        self.target_name = target_name
        self.source_path = source_path


class ExternalInputError(CompileError):
    """Raised when an external input subprocess fails."""

    def __init__(
        self,
        message="",
        *,
        target_name=None,
        source_path=None,
        command=None,
        returncode=None,
        stderr=None,
    ):
        super().__init__(message, target_name=target_name, source_path=source_path)
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class InventoryError(UserError):
    """Raised when the inventory cannot be loaded or resolved."""

    def __init__(self, message="", *, target_name=None):
        super().__init__(message)
        self.target_name = target_name


class InventoryValidationError(InventoryError):
    """Raised when inventory data fails schema validation."""


class InvalidTargetError(InventoryError):
    """Raised when a requested target does not exist in the inventory."""


# ---------------------------------------------------------------------------
# BackendError branch
# ---------------------------------------------------------------------------


class SecretError(BackendError):
    """Raised for general secret handling failures."""

    def __init__(self, message="", *, target_name=None):
        super().__init__(message)
        self.target_name = target_name


class RefError(BackendError):
    """Raised when a reference cannot be resolved or created."""

    def __init__(self, message="", *, target_name=None, ref_path=None):
        super().__init__(message)
        self.target_name = target_name
        self.ref_path = ref_path


class RefBackendError(BackendError):
    """Raised for failures in a reference storage backend."""


class RefFromFuncError(BackendError):
    """Raised when a ref-from-function evaluation fails."""


class RefHashMismatchError(BackendError):
    """Raised when a reference data hash does not match the stored hash."""


class HelmBindingUnavailableError(BackendError):
    """Raised when the helm input type is used but the binding is not available."""


class HelmFetchingError(BackendError):
    """Raised when fetching a helm chart fails."""

    def __init__(self, message="", *, chart_path=None):
        super().__init__(message)
        self.chart_path = chart_path


class HelmTemplateError(BackendError):
    """Raised when helm template rendering fails."""

    def __init__(self, message="", *, target_name=None, chart_path=None):
        super().__init__(message)
        self.target_name = target_name
        self.chart_path = chart_path


class GitSubdirNotFoundError(BackendError):
    """Raised when the requested subdirectory is not found in a git dependency."""


class GitFetchingError(BackendError):
    """Raised when a git repository cannot be fetched (not found or permission error)."""

    def __init__(self, message="", *, source=None):
        super().__init__(message)
        self.source = source


class RequestUnsuccessfulError(BackendError):
    """Raised when an HTTP request returns a non-success status."""


class KubernetesManifestValidationError(BackendError):
    """Raised when a Kubernetes manifest fails schema validation."""


class KustomizeTemplateError(BackendError):
    """Raised when kustomize template rendering fails."""


class CuelangTemplateError(BackendError):
    """Raised when cuelang template rendering fails."""


class MissingOptionalDependencyError(KapitanError):
    """Raised when a feature requires an optional dependency that is not installed.

    The message always names the pip install extra so the user knows exactly what to run.
    """

    def __init__(self, feature: str, extra: str):
        super().__init__(
            f"{feature} requires the '{extra}' optional dependency. "
            f"Install it with: pip install 'kapitan[{extra}]'"
        )
        self.feature = feature
        self.extra = extra
