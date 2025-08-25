"""Output formatters for different display modes."""

from rich.console import Console

from ..config import KapitanConfig, OutputFormat
from .base import OutputFormatter
from .console import ConsoleFormatter
from .json_formatter import JSONFormatter
from .plain import PlainFormatter


def create_formatter(config: KapitanConfig, console: Console | None = None) -> OutputFormatter:
    """Factory function to create the appropriate formatter."""
    if config.global_.output_format == OutputFormat.JSON:
        return JSONFormatter(config, console)
    elif config.global_.output_format == OutputFormat.PLAIN:
        return PlainFormatter(config, console)
    else:  # CONSOLE or fallback
        return ConsoleFormatter(config, console)


__all__ = [
    "OutputFormatter",
    "ConsoleFormatter",
    "JSONFormatter",
    "PlainFormatter",
    "create_formatter"
]
