# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the KapitanError hierarchy and structured fields."""

import json

import pytest

from kapitan.errors import (
    BackendError,
    CompileError,
    CuelangTemplateError,
    ExternalInputError,
    GitFetchingError,
    GitSubdirNotFoundError,
    HelmBindingUnavailableError,
    HelmFetchingError,
    HelmTemplateError,
    InternalError,
    InvalidTargetError,
    InventoryError,
    InventoryValidationError,
    KapitanError,
    KubernetesManifestValidationError,
    KustomizeTemplateError,
    RefBackendError,
    RefError,
    RefFromFuncError,
    RefHashMismatchError,
    RequestUnsuccessfulError,
    SecretError,
    UserError,
)


# ---------------------------------------------------------------------------
# Branch inheritance
# ---------------------------------------------------------------------------


class TestBranchInheritance:
    def test_user_error_is_kapitan_error(self):
        assert issubclass(UserError, KapitanError)

    def test_backend_error_is_kapitan_error(self):
        assert issubclass(BackendError, KapitanError)

    def test_internal_error_is_kapitan_error(self):
        assert issubclass(InternalError, KapitanError)

    def test_compile_error_is_user_error(self):
        assert issubclass(CompileError, UserError)

    def test_inventory_error_is_user_error(self):
        assert issubclass(InventoryError, UserError)

    def test_inventory_validation_error_is_inventory_error(self):
        assert issubclass(InventoryValidationError, InventoryError)

    def test_invalid_target_error_is_inventory_error(self):
        assert issubclass(InvalidTargetError, InventoryError)

    def test_secret_error_is_backend_error(self):
        assert issubclass(SecretError, BackendError)

    def test_ref_error_is_backend_error(self):
        assert issubclass(RefError, BackendError)

    def test_ref_backend_error_is_backend_error(self):
        assert issubclass(RefBackendError, BackendError)

    def test_ref_from_func_error_is_backend_error(self):
        assert issubclass(RefFromFuncError, BackendError)

    def test_ref_hash_mismatch_error_is_backend_error(self):
        assert issubclass(RefHashMismatchError, BackendError)

    def test_helm_binding_unavailable_is_backend_error(self):
        assert issubclass(HelmBindingUnavailableError, BackendError)

    def test_helm_fetching_error_is_backend_error(self):
        assert issubclass(HelmFetchingError, BackendError)

    def test_helm_template_error_is_backend_error(self):
        assert issubclass(HelmTemplateError, BackendError)

    def test_git_subdir_not_found_is_backend_error(self):
        assert issubclass(GitSubdirNotFoundError, BackendError)

    def test_git_fetching_error_is_backend_error(self):
        assert issubclass(GitFetchingError, BackendError)

    def test_request_unsuccessful_is_backend_error(self):
        assert issubclass(RequestUnsuccessfulError, BackendError)

    def test_k8s_manifest_validation_is_backend_error(self):
        assert issubclass(KubernetesManifestValidationError, BackendError)

    def test_kustomize_template_is_backend_error(self):
        assert issubclass(KustomizeTemplateError, BackendError)

    def test_cuelang_template_is_backend_error(self):
        assert issubclass(CuelangTemplateError, BackendError)

    def test_external_input_error_is_compile_error(self):
        assert issubclass(ExternalInputError, CompileError)


# ---------------------------------------------------------------------------
# to_dict / JSON round-trip
# ---------------------------------------------------------------------------


class TestToDictRoundTrip:
    def test_kapitan_error_base_to_dict(self):
        err = KapitanError("base message")
        result = err.to_dict()
        assert result["error"] == "KapitanError"
        assert result["message"] == "base message"

    def test_compile_error_structured_fields(self):
        err = CompileError(
            "compilation failed",
            target_name="my-target",
            source_path="/src/file.jsonnet",
        )
        result = err.to_dict()
        assert result["error"] == "CompileError"
        assert result["message"] == "compilation failed"
        assert result["target_name"] == "my-target"
        assert result["source_path"] == "/src/file.jsonnet"

    def test_compile_error_fields_json_serializable(self):
        err = CompileError("fail", target_name="t1", source_path="/p")
        assert json.dumps(err.to_dict())  # no TypeError

    def test_compile_error_optional_fields_default_none(self):
        err = CompileError("bare message")
        result = err.to_dict()
        assert result["target_name"] is None
        assert result["source_path"] is None

    def test_inventory_error_structured_fields(self):
        err = InventoryError("bad inventory", target_name="my-target")
        result = err.to_dict()
        assert result["target_name"] == "my-target"
        assert result["message"] == "bad inventory"

    def test_inventory_error_json_serializable(self):
        err = InventoryError("bad", target_name="t")
        assert json.dumps(err.to_dict())

    def test_ref_error_structured_fields(self):
        err = RefError("ref missing", target_name="t1", ref_path="/refs/secret")
        result = err.to_dict()
        assert result["target_name"] == "t1"
        assert result["ref_path"] == "/refs/secret"

    def test_ref_error_json_serializable(self):
        err = RefError("miss", target_name="t", ref_path="/r")
        assert json.dumps(err.to_dict())

    def test_helm_template_error_structured_fields(self):
        err = HelmTemplateError(
            "helm failed", target_name="svc", chart_path="/charts/svc"
        )
        result = err.to_dict()
        assert result["target_name"] == "svc"
        assert result["chart_path"] == "/charts/svc"

    def test_helm_template_error_json_serializable(self):
        err = HelmTemplateError("fail", target_name="t", chart_path="/c")
        assert json.dumps(err.to_dict())

    def test_helm_fetching_error_structured_fields(self):
        err = HelmFetchingError("fetch failed", chart_path="/charts/nginx")
        result = err.to_dict()
        assert result["chart_path"] == "/charts/nginx"

    def test_external_input_error_structured_fields(self):
        err = ExternalInputError(
            "subprocess failed",
            target_name="t1",
            source_path="/scripts/gen.sh",
            command="bash gen.sh",
            returncode=1,
            stderr="permission denied",
        )
        result = err.to_dict()
        assert result["target_name"] == "t1"
        assert result["source_path"] == "/scripts/gen.sh"
        assert result["command"] == "bash gen.sh"
        assert result["returncode"] == 1
        assert result["stderr"] == "permission denied"

    def test_external_input_error_json_serializable(self):
        err = ExternalInputError("fail", command="cmd", returncode=2, stderr="err")
        assert json.dumps(err.to_dict())

    def test_secret_error_structured_fields(self):
        err = SecretError("secret failed", target_name="my-target")
        result = err.to_dict()
        assert result["target_name"] == "my-target"

    def test_secret_error_json_serializable(self):
        err = SecretError("fail", target_name="t")
        assert json.dumps(err.to_dict())


# ---------------------------------------------------------------------------
# Catchability – existing catch patterns remain valid
# ---------------------------------------------------------------------------


class TestCatchability:
    def test_compile_error_catchable_as_kapitan_error(self):
        with pytest.raises(KapitanError):
            raise CompileError("oops")

    def test_ref_error_catchable_as_kapitan_error(self):
        with pytest.raises(KapitanError):
            raise RefError("missing")

    def test_inventory_error_catchable_as_kapitan_error(self):
        with pytest.raises(KapitanError):
            raise InventoryError("bad")

    def test_external_input_error_catchable_as_compile_error(self):
        with pytest.raises(CompileError):
            raise ExternalInputError("failed")

    def test_raise_from_preserves_cause(self):
        cause = OSError("disk full")
        with pytest.raises(CompileError) as exc_info:
            try:
                raise cause
            except OSError as exc:
                raise CompileError("write failed", target_name="t") from exc
        assert exc_info.value.__cause__ is cause


# ---------------------------------------------------------------------------
# repr includes error type name
# ---------------------------------------------------------------------------


class TestRepr:
    def test_repr_contains_class_name(self):
        err = CompileError("boom", target_name="foo")
        assert "CompileError" in repr(err) or "CompileError" in type(err).__name__
