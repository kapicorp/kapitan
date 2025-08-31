"""Abstract base class for output formatting implementations.

Defines the interface that all output formatters must implement
for consistent display across console, plain text, and JSON formats.
Each formatter handles the presentation of compilation results,
inventory data, and error messages in its specific format.
"""

from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console

from ..config import KapitanConfig
from ..models import CLIResult, CompilationResult, InventoryResult


class OutputFormatter(ABC):
    """Abstract interface for output formatting implementations.
    
    Defines the contract for displaying compilation results, inventory data,
    and error messages across different output formats. Implementations
    handle format-specific presentation logic.
    
    Attributes:
        config: Application configuration for formatting preferences.
        console: Rich console instance for output (may be null for some formats).
    """

    def __init__(self, config: KapitanConfig, console: Console | None = None):
        """Initialize formatter with configuration and console.
        
        Args:
            config: Application configuration.
            console: Rich console instance, creates default if None.
        """
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
