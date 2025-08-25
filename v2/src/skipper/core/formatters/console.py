"""Rich console output formatter."""

from typing import Any

from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..models import CLIResult, CompilationResult, InventoryResult
from .base import OutputFormatter


class ConsoleFormatter(OutputFormatter):
    """Rich console output formatter."""

    def show_configuration(self) -> None:
        """Show configuration panel with Rich formatting."""
        if not self.config.global_.verbose:
            return

        config_table = Table(show_header=False, box=None, padding=(0, 1))
        config_table.add_column("Key", style="cyan")
        config_table.add_column("Value", style="white")

        config_table.add_row("Config Source", ", ".join(self.config._sources))
        config_table.add_row("Parallel Jobs", str(self.config.global_.parallel_jobs))
        config_table.add_row("Verbose", str(self.config.global_.verbose))
        config_table.add_row("Output Format", self.config.global_.output_format.value)
        config_table.add_row("Inventory Path", str(self.config.global_.inventory_path))
        config_table.add_row("Output Path", str(self.config.global_.output_path))

        if self.config.logging.show_time:
            config_table.add_row("Show Time", str(self.config.logging.show_time))

        panel = Panel(config_table, title="Configuration", border_style="dim")
        self.console.print(panel)

    def show_compilation_start(self, inventory_path: str, output_path: str,
                             target_patterns: list[str], parallel_jobs: int) -> None:
        """Show compilation start with Rich formatting."""
        targets_str = ", ".join(target_patterns) if target_patterns else "all"

        self.console.print(f"[bold cyan]Compiling targets:[/bold cyan] {targets_str}")
        self.console.print(f"[dim]Inventory path:[/dim] {inventory_path}")
        self.console.print(f"[dim]Output path:[/dim] {output_path}")
        self.console.print(f"[dim]Parallel jobs:[/dim] {parallel_jobs}")

    def show_inventory_start(self) -> None:
        """Show inventory loading start."""
        pass  # Progress will handle this

    def show_inventory_result(self, result: InventoryResult) -> None:
        """Show inventory result with Rich formatting."""
        if result.success:
            backend_info = f" ({result.backend})" if result.backend else ""
            duration_str = f" in {result.duration:.2f}s" if result.duration else ""
            self.console.print(f"[green]Inventory loaded[/green] - {result.targets_found} targets found{duration_str}{backend_info}")
        else:
            error_msg = f": {result.error}" if result.error else ""
            self.console.print(f"[red]Inventory failed[/red]{error_msg}")

    def show_compilation_progress(self, progress_data: dict[str, Any]) -> Progress:
        """Show compilation progress with Rich progress bars."""
        _ = progress_data  # Unused for now
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        )
        progress.start()
        return progress

    def update_compilation_progress(self, context: Progress, progress_data: dict[str, Any]) -> None:
        """Update compilation progress bars."""
        _ = context, progress_data  # Unused for now - would update progress bars
        pass

    def show_compilation_result(self, result: CompilationResult) -> None:
        """Show final compilation result."""
        if result.success:
            self.console.print(f"[green]Compilation completed:[/green] {result.completed}/{result.total} targets")
            self.console.print("[green]Status: SUCCESS[/green]")
        else:
            self.console.print(f"[red]Compilation failed:[/red] {result.completed}/{result.total} targets completed, {result.failed} failed")
            self.console.print("[red]Status: FAILED[/red]")

    def show_targets_list(self, targets: list[str]) -> None:
        """Show list of targets."""
        if targets:
            self.console.print(f"[bold]Available targets ({len(targets)}):[/bold]")
            for target in targets:
                self.console.print(f"  • {target}")
        else:
            self.console.print("[yellow]No targets found[/yellow]")

    def show_error(self, error: str, details: str | None = None) -> None:
        """Show error with Rich formatting."""
        self.console.print(f"[red bold]ERROR:[/red bold] {error}")
        if details:
            self.console.print(f"[dim]{details}[/dim]")

    def finalize_output(self, result: CLIResult) -> None:
        """Finalize console output."""
        # Console output is already sent, no finalization needed
        pass
