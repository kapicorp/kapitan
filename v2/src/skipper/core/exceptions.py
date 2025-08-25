"""Exception classes for Kapitan."""

from typing import Any


class KapitanError(Exception):
    """Base exception class for Kapitan."""

    def __init__(self, message: str, *args: Any) -> None:
        super().__init__(message, *args)
        self.message = message


class CompileError(KapitanError):
    """Exception raised during compilation."""
    pass


class InventoryError(KapitanError):
    """Exception raised during inventory processing."""
    pass


class InputError(KapitanError):
    """Exception raised during input processing."""
    pass


class ValidationError(KapitanError):
    """Exception raised during validation."""
    pass


class RefsError(KapitanError):
    """Exception raised during refs processing."""
    pass
