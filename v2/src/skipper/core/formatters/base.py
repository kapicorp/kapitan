"""Base output formatter interface."""

from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console

from ..config import KapitanConfig
from ..models import CLIResult, CompilationResult, InventoryResult


class OutputFormatter(ABC):
    """Base class for output formatters."""

    def __init__(self, config: KapitanConfig, console: Console | None = None):
        self.config = config
        self.console = console or Console()

    @abstractmethod
    def show_configuration(self) -> None:
        """Show configuration information."""
        pass

    @abstractmethod
    def show_compilation_start(self, inventory_path: str, output_path: str,
                             target_patterns: list[str], parallel_jobs: int) -> None:
        """Show compilation start information."""
        pass

    @abstractmethod
    def show_inventory_start(self) -> None:
        """Show inventory loading start."""
        pass

    @abstractmethod
    def show_inventory_result(self, result: InventoryResult) -> None:
        """Show inventory loading result."""
        pass

    @abstractmethod
    def show_compilation_progress(self, progress_data: dict[str, Any]) -> Any:
        """Show compilation progress. Returns progress context if needed."""
        pass

    @abstractmethod
    def update_compilation_progress(self, context: Any, progress_data: dict[str, Any]) -> None:
        """Update compilation progress."""
        pass

    @abstractmethod
    def show_compilation_result(self, result: CompilationResult) -> None:
        """Show final compilation result."""
        pass

    @abstractmethod
    def show_targets_list(self, targets: list[str]) -> None:
        """Show list of targets."""
        pass

    @abstractmethod
    def show_error(self, error: str, details: str | None = None) -> None:
        """Show error message."""
        pass

    @abstractmethod
    def finalize_output(self, result: CLIResult) -> None:
        """Finalize and output the result."""
        pass

    def needs_silent_compilation(self) -> bool:
        """Return True if this formatter requires silent compilation mode."""
        return False
