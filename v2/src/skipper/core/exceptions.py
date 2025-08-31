"""Custom exception hierarchy for Skipper error handling.

Defines a structured exception hierarchy for different types of errors
that can occur during compilation, inventory processing, and validation.
All exceptions inherit from KapitanError for consistent error handling.
"""

from typing import Any


class KapitanError(Exception):
    """Base exception class for all Skipper-related errors.
    
    Provides a common base for all application-specific exceptions
    with consistent message handling and error context.
    
    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str, *args: Any) -> None:
        """Initialize exception with message and optional arguments.
        
        Args:
            message: Error description.
            *args: Additional arguments passed to Exception.
        """
        super().__init__(message, *args)
        self.message = message


class CompileError(KapitanError):
    """Exception raised when target compilation fails.
    
    Indicates errors during the target compilation phase, such as
    template rendering failures, invalid configurations, or output
    generation problems.
    """
    pass


class InventoryError(KapitanError):
    """Exception raised when inventory loading or parsing fails.
    
    Indicates problems with inventory structure, missing files,
    invalid YAML/JSON content, or target resolution issues.
    """
    pass


class InputError(KapitanError):
    """Exception raised when input processing encounters errors.
    
    Covers errors in input type handling, template processing,
    and data transformation during compilation.
    """
    pass


class ValidationError(KapitanError):
    """Exception raised when configuration or output validation fails.
    
    Indicates schema validation failures, constraint violations,
    or other validation rule breaches.
    """
    pass


class RefsError(KapitanError):
    """Exception raised when reference resolution fails.
    
    Covers errors in Kapitan reference processing, including
    secret resolution, credential access, and reference lookup failures.
    """
    pass
