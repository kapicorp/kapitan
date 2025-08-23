"""Main CLI entry point for Kapitan."""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.traceback import install

from kapitan import __version__
from kapitan.core.config import KapitanConfig, LogLevel, OutputFormat, get_config, reload_config
from kapitan.core.exceptions import KapitanError
from kapitan.core.compiler import CompilationSimulator

# Install rich traceback handling
install(show_locals=True)

# Create rich console
console = Console()

app = typer.Typer(
    name="kapitan",
    help="Kapitan - Generic templated configuration management",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Global state
_config: Optional[KapitanConfig] = None
logger = logging.getLogger("kapitan")


def get_app_config() -> KapitanConfig:
    """Get the application configuration."""
    global _config
    if _config is None:
        _config = get_config()
    return _config


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        config = get_app_config()
        if config.global_.output_format == OutputFormat.JSON:
            print(json.dumps({"version": __version__}))
        else:
            console.print(f"[bold blue]kapitan[/bold blue] [green]{__version__}[/green]")
        raise typer.Exit()


def configure_logging(config: KapitanConfig, verbose_override: Optional[bool] = None, json_override: Optional[bool] = None) -> None:
    """Configure logging based on configuration and CLI overrides."""
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Determine settings with CLI overrides taking precedence
    verbose = verbose_override if verbose_override is not None else config.global_.verbose
    json_output = json_override if json_override is not None else (config.global_.output_format == OutputFormat.JSON)
    plain_output = config.global_.output_format == OutputFormat.PLAIN
    log_level = LogLevel.DEBUG if verbose else config.logging.level
    
    # Convert log level to logging constant
    if isinstance(log_level, str):
        level = getattr(logging, log_level)
    else:
        level = getattr(logging, log_level.value)
    
    if json_output or config.logging.json_format:
        # For JSON output, use basic logging to stderr
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        ))
    elif plain_output:
        # For plain output, use simple text logging
        handler = logging.StreamHandler(sys.stderr)
        if verbose or config.logging.show_time:
            handler.setFormatter(logging.Formatter(
                '[%(asctime)s] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
        else:
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    else:
        # Use Rich logging for console output
        handler = RichHandler(
            console=console,
            show_time=verbose or config.logging.show_time,
            show_path=verbose or config.logging.show_path,
            rich_tracebacks=True,
            tracebacks_show_locals=verbose
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    
    logger.addHandler(handler)
    logger.setLevel(level)
    
    if verbose and not (json_output or plain_output):
        console.print("[dim]Verbose mode enabled[/dim]", style="blue")
    elif verbose and plain_output:
        print("Verbose mode enabled", file=sys.stderr)


def output_result(data: Dict[str, Any], success: bool = True) -> None:
    """Output result in the specified format."""
    config = get_app_config()
    if config.global_.output_format == OutputFormat.JSON:
        result = {
            "success": success,
            "data": data,
            "timestamp": time.time()
        }
        # Always prettify JSON output to stdout
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    elif config.global_.output_format == OutputFormat.PLAIN:
        # Plain text output for CI/pipes
        status = "SUCCESS" if success else "FAILED"
        print(f"Status: {status}")
        if config.global_.verbose:
            for key, value in data.items():
                print(f"{key}: {value}")
    else:
        # Rich console output is handled in each command
        pass


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: Optional[bool] = typer.Option(
        None,
        "--verbose",
        "-v",
        help="Enable verbose output (overrides config)",
    ),
    json_output: Optional[bool] = typer.Option(
        None,
        "--json",
        help="Output in JSON format (overrides config)",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """[bold blue]Kapitan[/bold blue] - Generic templated configuration management."""
    global _config
    
    # Load configuration
    try:
        if config_file:
            _config = reload_config(config_file)
        else:
            _config = get_app_config()
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    
    # Apply CLI overrides to global config
    if verbose is not None:
        _config.global_.verbose = verbose
    if json_output is not None:
        _config.global_.output_format = OutputFormat.JSON if json_output else OutputFormat.CONSOLE
    
    # Configure logging
    configure_logging(_config, verbose, json_output)
    
    logger.debug(f"Configuration loaded from: {config_file or 'default locations'}")


@app.command()
def compile(
    inventory_path: Optional[str] = typer.Option(
        None,
        "--inventory-path",
        "-i",
        help="Path to inventory directory (overrides config)",
    ),
    output_path: Optional[str] = typer.Option(
        None,
        "--output-path",
        "-o", 
        help="Path to output directory (overrides config)",
    ),
    targets: Optional[list[str]] = typer.Option(
        None,
        "--targets",
        "-t",
        help="Target names to compile (default: all)",
    ),
) -> None:
    """[green]Compile[/green] configuration for targets."""
    try:
        config = get_app_config()
        
        # Use CLI args or fall back to config
        inv_path = inventory_path or config.global_.inventory_path
        out_path = output_path or config.global_.output_path
        
        # Handle comma-separated targets from CLI
        if targets:
            target_list = []
            for target in targets:
                # Split comma-separated values
                target_list.extend([t.strip() for t in target.split(",") if t.strip()])
        else:
            target_list = ["all"]
        
        logger.info("Starting compilation")
        logger.debug(f"Inventory path: {inv_path}")
        logger.debug(f"Output path: {out_path}")
        logger.debug(f"Targets: {', '.join(target_list)}")
        logger.debug(f"Parallel jobs: {config.global_.parallel_jobs}")
        
        if config.global_.output_format == OutputFormat.CONSOLE:
            # Only show configuration panel in verbose mode
            if config.global_.verbose:
                info_table = Table.grid(padding=1)
                info_table.add_column(style="cyan", no_wrap=True)
                info_table.add_column()
                
                info_table.add_row("Inventory path:", f"[yellow]{inv_path}[/yellow]")
                info_table.add_row("Output path:", f"[yellow]{out_path}[/yellow]")
                info_table.add_row("Targets:", f"[yellow]{', '.join(target_list)}[/yellow]")
                info_table.add_row("Parallel jobs:", f"[yellow]{config.global_.parallel_jobs}[/yellow]")
                
                console.print(Panel(info_table, title="[bold green]Compilation Configuration[/bold green]"))
            
            # Run compilation simulation with parallel processes
            simulator = CompilationSimulator(console, parallel_jobs=config.global_.parallel_jobs, output_path=out_path, inventory_path=inv_path)
            compilation_result = simulator.run_compilation(target_list)
        elif config.global_.output_format == OutputFormat.PLAIN:
            # Plain text output for CI/pipes
            print(f"Compiling targets: {', '.join(target_list)}")
            print(f"Inventory path: {inv_path}")
            print(f"Output path: {out_path}")
            print(f"Parallel jobs: {config.global_.parallel_jobs}")
            
            # Run compilation simulation for plain output (silent mode)
            simulator = CompilationSimulator(Console(file=None), parallel_jobs=config.global_.parallel_jobs, silent=True, output_path=out_path, inventory_path=inv_path)
            compilation_result = simulator.run_compilation(target_list)
            
            # Show plain text results
            print(f"Compilation completed: {compilation_result['completed']}/{compilation_result['total']} targets")
            if compilation_result['failed'] > 0:
                print(f"Failed targets: {compilation_result['failed']}")
        else:
            # JSON output (silent mode)
            simulator = CompilationSimulator(Console(file=None), parallel_jobs=config.global_.parallel_jobs, silent=True, output_path=out_path, inventory_path=inv_path)
            compilation_result = simulator.run_compilation(target_list)
        
        # Prepare result data
        result_data = {
            "inventory_path": inv_path,
            "output_path": out_path,
            "targets": target_list,
            "parallel_jobs": config.global_.parallel_jobs,
            "compilation_result": compilation_result,
            "status": "completed" if compilation_result["success"] else "failed"
        }
        
        output_result(result_data, success=compilation_result["success"])
        
        if compilation_result["success"]:
            logger.info("Compilation completed successfully")
        else:
            logger.error(f"Compilation failed: {compilation_result['failed']} targets failed")
        
    except KapitanError as e:
        error_data = {"error": "KapitanError", "message": e.message}
        config = get_app_config()
        if config.global_.output_format == OutputFormat.CONSOLE:
            console.print(f"[red]❌ Kapitan error:[/red] {e.message}")
        elif config.global_.output_format == OutputFormat.PLAIN:
            print(f"ERROR: {e.message}")
        output_result(error_data, success=False)
        logger.error(f"Kapitan error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        error_data = {"error": "UnexpectedError", "message": str(e)}
        config = get_app_config()
        if config.global_.output_format == OutputFormat.CONSOLE:
            console.print(f"[red]❌ Unexpected error:[/red] {e}")
            if config.global_.verbose:
                console.print_exception(show_locals=True)
        elif config.global_.output_format == OutputFormat.PLAIN:
            print(f"ERROR: {e}")
        output_result(error_data, success=False)
        logger.error(f"Unexpected error: {e}", exc_info=config.global_.verbose)
        raise typer.Exit(1)


@app.command()
def inventory(
    inventory_path: Optional[str] = typer.Option(
        None,
        "--inventory-path", 
        "-i",
        help="Path to inventory directory (overrides config)",
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        "-t",
        help="Target name to show inventory for",
    ),
) -> None:
    """[blue]Show[/blue] inventory for targets."""
    try:
        config = get_app_config()
        
        # Use CLI args or fall back to config
        inv_path = inventory_path or config.global_.inventory_path
        target_name = target if target else "all"
        
        logger.info("Showing inventory")
        logger.debug(f"Inventory path: {inv_path}")
        logger.debug(f"Target: {target_name}")
        
        if config.global_.output_format == OutputFormat.CONSOLE:
            # Create a rich panel for inventory info
            info_table = Table.grid(padding=1)
            info_table.add_column(style="cyan", no_wrap=True)
            info_table.add_column()
            
            info_table.add_row("Inventory path:", f"[yellow]{inv_path}[/yellow]")
            info_table.add_row("Target:", f"[yellow]{target_name}[/yellow]")
            
            console.print(Panel(info_table, title="[bold blue]Inventory Configuration[/bold blue]"))
            
            console.print("[yellow]⚠️  Inventory logic not yet implemented[/yellow]")
            
            # Example of what inventory output might look like
            if config.global_.verbose:
                example_table = Table(title="Example Inventory Structure")
                example_table.add_column("Target", style="cyan", no_wrap=True)
                example_table.add_column("Classes", style="magenta")
                example_table.add_column("Parameters", style="green")
                
                example_table.add_row("webapp", "common, nginx", "replicas: 3")
                example_table.add_row("database", "common, postgres", "version: 14")
                
                console.print(example_table)
        elif config.global_.output_format == OutputFormat.PLAIN:
            # Plain text output for CI/pipes
            print(f"Inventory path: {inv_path}")
            print(f"Target: {target_name}")
            print("WARNING: Inventory logic not yet implemented")
            
            # Example output in verbose mode
            if config.global_.verbose:
                print("\nExample inventory structure:")
                print("webapp: classes=[common, nginx], replicas=3")
                print("database: classes=[common, postgres], version=14")
        
        # Prepare result data
        result_data = {
            "inventory_path": inv_path,
            "target": target_name,
            "status": "not_implemented",
            "message": "Inventory logic not yet implemented",
            "example_data": [
                {"target": "webapp", "classes": ["common", "nginx"], "parameters": {"replicas": 3}},
                {"target": "database", "classes": ["common", "postgres"], "parameters": {"version": 14}}
            ] if config.global_.verbose else None
        }
        
        output_result(result_data, success=False)
        logger.warning("Inventory logic not yet implemented")
        
    except KapitanError as e:
        error_data = {"error": "KapitanError", "message": e.message}
        config = get_app_config()
        if config.global_.output_format == OutputFormat.CONSOLE:
            console.print(f"[red]❌ Kapitan error:[/red] {e.message}")
        elif config.global_.output_format == OutputFormat.PLAIN:
            print(f"ERROR: {e.message}")
        output_result(error_data, success=False)
        logger.error(f"Kapitan error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        error_data = {"error": "UnexpectedError", "message": str(e)}
        config = get_app_config()
        if config.global_.output_format == OutputFormat.CONSOLE:
            console.print(f"[red]❌ Unexpected error:[/red] {e}")
            if config.global_.verbose:
                console.print_exception(show_locals=True)
        elif config.global_.output_format == OutputFormat.PLAIN:
            print(f"ERROR: {e}")
        output_result(error_data, success=False)
        logger.error(f"Unexpected error: {e}", exc_info=config.global_.verbose)
        raise typer.Exit(1)


@app.command()
def init(
    path: Optional[str] = typer.Option(
        None,
        "--path",
        "-p",
        help="Path to initialize project in",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force initialization even if directory is not empty",
    ),
) -> None:
    """[magenta]Initialize[/magenta] a new Kapitan project."""
    try:
        config = get_app_config()
        
        # Use CLI args or fall back to current directory
        project_path = path or "."
        
        logger.info("Initializing Kapitan project")
        logger.debug(f"Path: {project_path}")
        logger.debug(f"Force mode: {force}")
        
        if config.global_.output_format == OutputFormat.CONSOLE:
            # Create a rich panel for init info
            info_table = Table.grid(padding=1)
            info_table.add_column(style="cyan", no_wrap=True)
            info_table.add_column()
            
            info_table.add_row("Path:", f"[yellow]{project_path}[/yellow]")
            info_table.add_row("Force mode:", "[red]enabled[/red]" if force else "[dim]disabled[/dim]")
            
            console.print(Panel(info_table, title="[bold magenta]Project Initialization[/bold magenta]"))
            
            console.print("[yellow]⚠️  Initialization logic not yet implemented[/yellow]")
            
            # Show what would be created
            if config.global_.verbose:
                console.print("\n[dim]Project structure that would be created:[/dim]")
                console.print(f"📁 {config.global_.inventory_path}/")
                console.print(f"  📁 classes/")
                console.print(f"  📁 targets/")
                console.print("📁 components/")
                console.print(f"📁 {config.global_.output_path}/")
                console.print("📄 kapitan.toml")
        elif config.global_.output_format == OutputFormat.PLAIN:
            # Plain text output for CI/pipes
            print(f"Initializing Kapitan project at: {project_path}")
            print(f"Force mode: {'enabled' if force else 'disabled'}")
            print("WARNING: Initialization logic not yet implemented")
            
            # Show what would be created in verbose mode
            if config.global_.verbose:
                print("\nProject structure that would be created:")
                print(f"  {config.global_.inventory_path}/")
                print(f"    classes/")
                print(f"    targets/")
                print("  components/")
                print(f"  {config.global_.output_path}/")
                print("  kapitan.toml")
        
        # Prepare result data
        project_structure = [
            f"{config.global_.inventory_path}/",
            f"{config.global_.inventory_path}/classes/",
            f"{config.global_.inventory_path}/targets/",
            "components/",
            f"{config.global_.output_path}/",
            "kapitan.toml"
        ] if config.global_.verbose else None
        
        result_data = {
            "path": project_path,
            "force": force,
            "status": "not_implemented",
            "message": "Initialization logic not yet implemented",
            "planned_structure": project_structure
        }
        
        output_result(result_data, success=False)
        logger.warning("Initialization logic not yet implemented")
        
    except KapitanError as e:
        error_data = {"error": "KapitanError", "message": e.message}
        config = get_app_config()
        if config.global_.output_format == OutputFormat.CONSOLE:
            console.print(f"[red]❌ Kapitan error:[/red] {e.message}")
        elif config.global_.output_format == OutputFormat.PLAIN:
            print(f"ERROR: {e.message}")
        output_result(error_data, success=False)
        logger.error(f"Kapitan error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        error_data = {"error": "UnexpectedError", "message": str(e)}
        config = get_app_config()
        if config.global_.output_format == OutputFormat.CONSOLE:
            console.print(f"[red]❌ Unexpected error:[/red] {e}")
            if config.global_.verbose:
                console.print_exception(show_locals=True)
        elif config.global_.output_format == OutputFormat.PLAIN:
            print(f"ERROR: {e}")
        output_result(error_data, success=False)
        logger.error(f"Unexpected error: {e}", exc_info=config.global_.verbose)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()