"""Test exception classes."""

import pytest

from kapitan.core.exceptions import (
    CompileError,
    InputError,
    InventoryError,
    KapitanError,
    RefsError,
    ValidationError,
)


def test_kapitan_error() -> None:
    """Test KapitanError base exception."""
    error = KapitanError("test error")
    assert str(error) == "test error"
    assert error.message == "test error"


def test_compile_error() -> None:
    """Test CompileError exception."""
    error = CompileError("compile failed")
    assert isinstance(error, KapitanError)
    assert str(error) == "compile failed"
    assert error.message == "compile failed"


def test_inventory_error() -> None:
    """Test InventoryError exception."""
    error = InventoryError("inventory failed")
    assert isinstance(error, KapitanError)
    assert str(error) == "inventory failed"


def test_input_error() -> None:
    """Test InputError exception."""
    error = InputError("input failed")
    assert isinstance(error, KapitanError)
    assert str(error) == "input failed"


def test_validation_error() -> None:
    """Test ValidationError exception."""
    error = ValidationError("validation failed")
    assert isinstance(error, KapitanError)
    assert str(error) == "validation failed"


def test_refs_error() -> None:
    """Test RefsError exception."""
    error = RefsError("refs failed")
    assert isinstance(error, KapitanError)
    assert str(error) == "refs failed"