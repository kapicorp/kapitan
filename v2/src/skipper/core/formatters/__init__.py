"""Output formatting system supporting multiple display modes.

Provides formatters for console (Rich), plain text (CI), and JSON (API) output.
The formatter selection is based on configuration and automatically adapts
to TTY detection for appropriate output in different environments.
"""

from rich.console import Console

from ..config import KapitanConfig, OutputFormat
from .base import OutputFormatter
from .console import ConsoleFormatter
from .json_formatter import JSONFormatter
from .plain import PlainFormatter


def create_formatter(config: KapitanConfig, console: Console | None = None) -> OutputFormatter:
    """Create appropriate output formatter based on configuration.
    
    Args:
        config: Application configuration containing output format preference.
        console: Optional Rich console instance.
        
    Returns:
        OutputFormatter instance configured for the specified format.
    """
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
