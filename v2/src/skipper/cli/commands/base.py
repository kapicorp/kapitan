"""Base utilities for CLI commands."""

import logging

import typer
from rich.console import Console

from ...core.config import KapitanConfig
from ...core.container import get_container
from ...core.decorators import handle_errors, require_config
from ...core.formatters import OutputFormatter

logger = logging.getLogger(__name__)


class CommandBase:
    """Base class for CLI commands with common functionality."""

    def __init__(self):
        self._container = get_container()

    def get_config(self) -> KapitanConfig:
        """Get application configuration via dependency injection."""
        return self._container.get('config')

    def get_console(self) -> Console:
        """Get console via dependency injection."""
        return self._container.get('console')

    def create_formatter(self, config: KapitanConfig | None = None) -> OutputFormatter:
        """Create output formatter for the current configuration."""
        if config is None:
            return self._container.get('formatter')
        else:
            # Create custom formatter with provided config
            from ...core.formatters import create_formatter
            return create_formatter(config, self.get_console())

    @property
    def console(self) -> Console:
        """Console property for backward compatibility."""
        return self.get_console()

    def resolve_path(self, provided_path: str | None, config_path: str, description: str) -> str:
        """Resolve a path from CLI argument or configuration."""
        if provided_path:
            return provided_path
        if config_path:
            return config_path
        raise typer.BadParameter(f"No {description} specified. Use --{description.replace(' ', '-')} or configure it in kapitan.toml")


def common_error_handler(*exception_types, **kwargs):
    """Decorator factory for common error handling patterns."""
    return handle_errors(*exception_types, **kwargs)


def command_with_config(func):
    """Decorator to ensure configuration is loaded for commands."""
    return require_config(func)
