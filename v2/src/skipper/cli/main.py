"""Main CLI entry point for Skipper (Kapitan v2).

This module provides the primary command-line interface for Skipper, featuring:
- Multi-format output (console, plain, JSON)
- Configuration management with precedence handling
- Rich logging and error reporting
- Auto-detection of TTY for appropriate output formatting
"""

import logging
import sys

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

from skipper import __version__
from skipper.cli.commands import compile_command, init_command, inventory_command, targets_command
from skipper.core.config import KapitanConfig, LogLevel, OutputFormat, get_config

# Install rich traceback handling
install(show_locals=True)

app = typer.Typer(
    name="kapitan",
    help="Kapitan - Generic templated configuration management",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

logger = logging.getLogger("kapitan")


def version_callback(value: bool) -> None:
    """Callback to display version information and exit.
    
    Args:
        value: If True, displays version and exits the application.
    """
    if value:
        typer.echo(f"Kapitan v{__version__}")
        raise typer.Exit()


def configure_logging(config: KapitanConfig, verbose: bool | None = None, json_output: bool | None = None):
    """Configure application logging with appropriate handlers and formatters.
    
    Sets up logging to use either Rich handlers for human-readable output or
    JSON handlers for programmatic consumption. Automatically configures
    log levels, output destinations, and formatting based on configuration.
    
    Args:
        config: Application configuration containing logging preferences.
        verbose: Override to enable debug-level logging.
        json_output: Override to force JSON log formatting.
    """
    # Determine log level
    log_level = LogLevel.DEBUG if verbose else config.logging.level

    # Determine if we should use JSON logging or Rich logging
    use_json = json_output if json_output is not None else config.logging.json_format

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.value)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if use_json:
        # JSON logging for programmatic consumption
        json_handler = logging.StreamHandler(sys.stderr)
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
        json_handler.setFormatter(json_formatter)
        root_logger.addHandler(json_handler)
    else:
        # Rich logging for human consumption
        rich_handler = RichHandler(
            console=Console(stderr=True),
            show_time=config.logging.show_time,
            show_path=config.logging.show_path,
        )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(rich_handler)


@app.callback()
def main(
    _version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: bool | None = typer.Option(
        None,
        "--verbose",
        "-v",
        help="Enable verbose output (overrides config)",
    ),
    json_output: bool | None = typer.Option(
        None,
        "--json",
        help="Output in JSON format (overrides config)",
        is_flag=True,
    ),
    _config_file: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Main CLI callback that handles global options and configuration.
    
    Processes global CLI options, loads configuration with proper precedence,
    sets up logging, and auto-detects output format based on TTY status.
    
    Args:
        _version: Triggers version display when True.
        verbose: Enables debug-level logging.
        json_output: Forces JSON output format.
        _config_file: Path to custom configuration file (not yet implemented).
        
    Raises:
        typer.Exit: On configuration loading errors or version display.
    """
    # Load configuration
    try:
        # TODO: Implement custom config file loading
        _config = get_config()
    except Exception as e:
        typer.echo(f"Error loading configuration: {e}", err=True)
        raise typer.Exit(1) from None

    # Override config with CLI flags
    if json_output is not None:
        _config.global_.output_format = OutputFormat.JSON if json_output else OutputFormat.CONSOLE

    # Auto-detect piping/redirection and default to plain format
    if json_output is None and not sys.stdout.isatty() and _config.global_.output_format == OutputFormat.CONSOLE:
        _config.global_.output_format = OutputFormat.PLAIN

    # Configure logging
    configure_logging(_config, verbose, json_output)

    logger.debug(f"Configuration loaded from: {', '.join(_config._sources)}")


# Register commands
app.command("targets", help="List available targets from inventory.")(targets_command)
app.command("compile", help="Compile configuration for targets.")(compile_command)
app.command("inventory", help="Browse inventory targets interactively.")(inventory_command)
app.command("init", help="Initialize a new Kapitan project.")(init_command)


if __name__ == "__main__":
    app()
