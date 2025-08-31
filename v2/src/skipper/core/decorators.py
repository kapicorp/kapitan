"""Decorators for cross-cutting concerns like error handling and logging.

Provides reusable decorators for:
- Consistent error handling with formatter integration
- Structured operation logging with context
- Path validation for file operations  
- Configuration requirement enforcement
"""

import functools
import logging
import sys
from collections.abc import Callable
from typing import Any, TypeVar

from .config import get_config
from .exceptions import KapitanError
from .formatters import create_formatter
from .models import CLIResult

T = TypeVar('T')
logger = logging.getLogger(__name__)


def handle_errors(*exception_types: type[Exception],
                  reraise: bool = False,
                  default_message: str | None = None,
                  exit_code: int = 1) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for consistent exception handling across CLI commands.
    
    Provides uniform error handling with formatter integration, logging,
    and appropriate exit behavior. Supports multiple output formats.
    
    Args:
        exception_types: Exception classes to catch and handle.
        reraise: Whether to reraise exception after handling.
        default_message: Fallback message if exception has no message.
        exit_code: Exit code for application termination.
        
    Returns:
        Decorator function that wraps the target function.
        
    Example:
        @handle_errors(FileNotFoundError, default_message="File not found")
        @handle_errors(KapitanError, reraise=True)
        def my_command():
            # command implementation
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                # Get config and create formatter for consistent error display
                try:
                    config = get_config()
                    from rich.console import Console
                    formatter = create_formatter(config, Console())

                    # Determine error message
                    if isinstance(e, KapitanError):
                        error_message = e.message
                        error_type = "KapitanError"
                    else:
                        error_message = str(e) or default_message or "An error occurred"
                        error_type = type(e).__name__

                    # Show error using formatter
                    formatter.show_error(error_type, error_message)

                    # Create result for JSON output
                    result = CLIResult(
                        success=False,
                        error=error_type,
                        message=error_message
                    )
                    formatter.finalize_output(result)

                    # Log the error
                    logger.error(f"{error_type}: {error_message}", exc_info=True)

                except Exception as format_error:
                    # Fallback error handling if formatter fails
                    print(f"ERROR: {e}", file=sys.stderr)
                    logger.error(f"Error handling failed: {format_error}", exc_info=True)

                if reraise:
                    raise
                else:
                    import typer
                    raise typer.Exit(exit_code) from None

        return wrapper
    return decorator


def log_execution(operation_name: str,
                  log_args: bool = False,
                  log_result: bool = False) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for structured logging of function execution.
    
    Provides consistent logging for operation start, completion, and failure
    with optional argument and result logging. Includes timing information
    and structured context for log analysis.
    
    Args:
        operation_name: Human-readable operation name for log context.
        log_args: Whether to include function arguments in logs.
        log_result: Whether to include function result in logs.
        
    Returns:
        Decorator function that adds logging to the target function.
        
    Example:
        @log_execution("target_resolution", log_args=True)
        def resolve_targets(self, patterns: list[str]) -> list[str]:
            # function implementation
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Create context for logging (avoid 'args' key which conflicts with logging)
            context = {"operation": operation_name, "function": func.__name__}

            if log_args:
                # Log arguments (be careful with sensitive data)
                safe_args = [str(arg)[:100] for arg in args[1:]]  # Skip 'self'
                safe_kwargs = {k: str(v)[:100] for k, v in kwargs.items()}
                context.update({"call_args": safe_args, "call_kwargs": safe_kwargs})

            logger.info(f"Starting {operation_name}", extra=context)

            try:
                result = func(*args, **kwargs)

                if log_result:
                    # Log result (truncate if too long)
                    result_str = str(result)[:200] if result else "None"
                    context["result"] = result_str

                logger.info(f"Completed {operation_name}", extra=context)
                return result

            except Exception as e:
                context["error"] = str(e)
                logger.error(f"Failed {operation_name}", extra=context)
                raise

        return wrapper
    return decorator


def validate_paths(*path_args: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to validate existence of specified path arguments.
    
    Checks that path arguments refer to existing files or directories
    before function execution. Raises FileNotFoundError for missing paths.
    
    Args:
        path_args: Parameter names that should be validated as existing paths.
        
    Returns:
        Decorator function that validates paths before execution.
        
    Raises:
        FileNotFoundError: If any specified path does not exist.
        
    Example:
        @validate_paths("inventory_path", "output_path")
        def my_command(inventory_path: str, output_path: str):
            # command implementation
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import inspect
            import os

            # Get function signature to map args to parameter names
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            # Validate specified path arguments
            for path_arg in path_args:
                if path_arg in bound.arguments:
                    path_value = bound.arguments[path_arg]
                    if path_value and not os.path.exists(path_value):
                        raise FileNotFoundError(f"Path does not exist: {path_value}")

            return func(*args, **kwargs)

        return wrapper
    return decorator


def require_config(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure configuration is loaded before command execution.
    
    Validates that application configuration can be loaded successfully
    before allowing command execution to proceed. Provides early failure
    for configuration issues.
    
    Args:
        func: Function to wrap with configuration requirement.
        
    Returns:
        Wrapped function that validates configuration availability.
        
    Raises:
        KapitanError: If configuration cannot be loaded.
        
    Example:
        @require_config
        def my_command():
            # command logic - config guaranteed available
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        # Ensure configuration is loaded
        try:
            config = get_config()
            logger.debug(f"Configuration loaded from: {', '.join(config._sources)}")
        except Exception as e:
            raise KapitanError(f"Failed to load configuration: {e}") from e

        return func(*args, **kwargs)

    return wrapper
