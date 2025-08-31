"""Base functionality and utilities for CLI command implementations.

Provides common infrastructure for all CLI commands including:
- Dependency injection access
- Configuration and console management
- Path resolution utilities
- Error handling decorators
"""

import logging

import typer
from rich.console import Console

from skipper.core.config import KapitanConfig
from skipper.core.container import get_container
from skipper.core.decorators import handle_errors, require_config
from skipper.core.formatters import OutputFormatter

logger = logging.getLogger(__name__)


class CommandBase:
    """Base class providing common functionality for all CLI commands.
    
    Handles dependency injection, configuration access, and common utilities
    that all commands need. Commands inherit from this class to get access
    to configuration, console output, and formatters.
    """

    def __init__(self):
        """Initialize command with dependency injection container."""
        self._container = get_container()

    def get_config(self) -> KapitanConfig:
        """Get application configuration from dependency injection container.
        
        Returns:
            Current application configuration instance.
        """
        return self._container.get('config')

    def get_console(self) -> Console:
        """Get Rich console instance from dependency injection container.
        
        Returns:
            Console instance for rich output formatting.
        """
        return self._container.get('console')

    def create_formatter(self, config: KapitanConfig | None = None) -> OutputFormatter:
        """Create appropriate output formatter based on configuration.
        
        Args:
            config: Optional configuration override, uses container config if None.
            
        Returns:
            OutputFormatter instance configured for current output format.
        """
        if config is None:
            return self._container.get('formatter')
        else:
            # Create custom formatter with provided config
            from skipper.core.formatters import create_formatter
            return create_formatter(config, self.get_console())

    @property
    def console(self) -> Console:
        """Console property for backward compatibility with legacy code.
        
        Returns:
            Console instance from dependency injection.
        """
        return self.get_console()

    def resolve_path(self, provided_path: str | None, config_path: str, description: str) -> str:
        """Resolve path with precedence: CLI argument > configuration > error.
        
        Args:
            provided_path: Path provided via CLI argument.
            config_path: Path from configuration file.
            description: Human-readable description for error messages.
            
        Returns:
            Resolved path string.
            
        Raises:
            typer.BadParameter: If no path can be resolved.
        """
        if provided_path:
            return provided_path
        if config_path:
            return config_path
        raise typer.BadParameter(f"No {description} specified. Use --{description.replace(' ', '-')} or configure it in kapitan.toml")


def common_error_handler(*exception_types, **kwargs):
    """Create error handling decorator for specified exception types.
    
    Args:
        *exception_types: Exception classes to handle.
        **kwargs: Additional options for error handling behavior.
        
    Returns:
        Decorator function for error handling.
    """
    return handle_errors(*exception_types, **kwargs)


def command_with_config(func):
    """Decorator that ensures configuration is loaded before command execution.
    
    Args:
        func: Command function to wrap.
        
    Returns:
        Wrapped function with configuration requirement.
    """
    return require_config(func)
