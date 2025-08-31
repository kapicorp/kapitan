"""JSON output formatter for programmatic use."""

import json
from typing import Any

from rich.console import Console

from ..config import KapitanConfig
from ..models import CLIResult, CompilationResult, InventoryResult
from .base import OutputFormatter


class JSONFormatter(OutputFormatter):
    """JSON output formatter for programmatic use."""

    def __init__(self, config: KapitanConfig, console: Console | None = None):
        super().__init__(config, console)
        self._result_data: dict[str, Any] = {}

    def show_configuration(self) -> None:
        """Store configuration in JSON data."""
        self._result_data["configuration"] = {
            "config_source": self.config._sources,
            "parallel_jobs": self.config.global_.parallel_jobs,
            "verbose": self.config.global_.verbose,
            "output_format": self.config.global_.output_format.value,
            "inventory_path": str(self.config.global_.inventory_path),
            "output_path": str(self.config.global_.output_path)
        }

    def show_compilation_start(self, inventory_path: str, output_path: str,
                             target_patterns: list[str], parallel_jobs: int) -> None:
        """Store compilation start data."""
        self._result_data["compilation_start"] = {
            "inventory_path": inventory_path,
            "output_path": output_path,
            "target_patterns": target_patterns,
            "parallel_jobs": parallel_jobs
        }

    def show_inventory_start(self) -> None:
        """Store inventory start data."""
        pass  # No action needed

    def show_inventory_result(self, result: InventoryResult) -> None:
        """Store inventory result data."""
        self._result_data["inventory_result"] = result.__dict__

    def show_compilation_progress(self, progress_data: dict[str, Any]) -> None:
        """Store compilation progress data."""
        _ = progress_data  # No progress display in JSON mode
        return None

    def update_compilation_progress(self, context: Any, progress_data: dict[str, Any]) -> None:
        """Update compilation progress."""
        _ = context, progress_data  # No progress updates in JSON mode
        pass

    def show_compilation_result(self, result: CompilationResult) -> None:
        """Store final compilation result."""
        self._result_data["compilation_result"] = result.__dict__

    def show_targets_list(self, targets: list[str]) -> None:
        """Store targets list."""
        self._result_data["targets"] = targets

    def show_error(self, error: str, details: str | None = None) -> None:
        """Store error data."""
        self._result_data["error"] = {
            "message": error,
            "details": details
        }

    def finalize_output(self, result: CLIResult) -> None:
        """Output final JSON result."""
        if hasattr(result, '__dict__'):
            self._result_data.update(result.__dict__)

        json_output = {
            "success": result.success if hasattr(result, 'success') else True,
            "data": self._result_data
        }

        print(json.dumps(json_output, indent=2, sort_keys=True, default=str))

    def needs_silent_compilation(self) -> bool:
        """JSON format requires silent compilation."""
        return True
