"""Common decorators for error handling and other cross-cutting concerns."""

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
    """
    Decorator to handle exceptions consistently across CLI commands.

    Args:
        exception_types: Exception types to handle
        reraise: Whether to reraise the exception after handling
        default_message: Default error message if none provided
        exit_code: Exit code to use when exiting

    Usage:
        @handle_errors(FileNotFoundError, default_message="File not found")
        @handle_errors(KapitanError, reraise=True)
        def my_command():
            # command logic
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
    """
    Decorator to log function execution with structured information.

    Args:
        operation_name: Name of the operation for logging context
        log_args: Whether to log function arguments
        log_result: Whether to log function result

    Usage:
        @log_execution("target_resolution", log_args=True)
        def resolve_targets(self, patterns: List[str]) -> List[str]:
            # function logic
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
    """
    Decorator to validate that specified path arguments exist.

    Args:
        path_args: Names of arguments that should be validated as paths

    Usage:
        @validate_paths("inventory_path", "output_path")
        def my_command(inventory_path: str, output_path: str):
            # command logic
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


def require_config[T](func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure configuration is loaded before command execution.

    Usage:
        @require_config
        def my_command():
            # command logic - config is guaranteed to be available
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
