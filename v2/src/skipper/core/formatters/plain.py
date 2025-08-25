"""Plain text formatter for CI/scripting."""

import sys
from typing import Any

from ..models import CLIResult, CompilationResult, InventoryResult
from .base import OutputFormatter


class PlainFormatter(OutputFormatter):
    """Plain text formatter for CI/scripting."""

    def show_configuration(self) -> None:
        """Show configuration in plain text."""
        if not self.config.global_.verbose:
            return

        print("Configuration:")
        print(f"  Config Source: {', '.join(self.config._sources)}")
        print(f"  Parallel Jobs: {self.config.global_.parallel_jobs}")
        print(f"  Verbose: {self.config.global_.verbose}")
        print(f"  Output Format: {self.config.global_.output_format.value}")
        print(f"  Inventory Path: {self.config.global_.inventory_path}")
        print(f"  Output Path: {self.config.global_.output_path}")

    def show_compilation_start(self, inventory_path: str, output_path: str,
                             target_patterns: list[str], parallel_jobs: int) -> None:
        """Show compilation start in plain text."""
        targets_str = ", ".join(target_patterns) if target_patterns else "all"
        print(f"Compiling targets: {targets_str}")
        print(f"Inventory path: {inventory_path}")
        print(f"Output path: {output_path}")
        print(f"Parallel jobs: {parallel_jobs}")

    def show_inventory_start(self) -> None:
        """Show inventory loading start."""
        pass  # Silent for plain output

    def show_inventory_result(self, result: InventoryResult) -> None:
        """Show inventory result in plain text."""
        _ = result  # Silent compilation for plain output
        pass

    def show_compilation_progress(self, progress_data: dict[str, Any]) -> None:
        """Show compilation progress in plain text."""
        _ = progress_data  # No progress bars in plain mode
        return None

    def update_compilation_progress(self, context: Any, progress_data: dict[str, Any]) -> None:
        """Update compilation progress."""
        _ = context, progress_data  # No progress updates in plain mode
        pass

    def show_compilation_result(self, result: CompilationResult) -> None:
        """Show final compilation result."""
        print(f"Compilation completed: {result.completed}/{result.total} targets")
        if result.success:
            print("Status: SUCCESS")
        else:
            print("Status: FAILED")

    def show_targets_list(self, targets: list[str]) -> None:
        """Show list of targets."""
        if targets:
            print(f"Available targets ({len(targets)}):")
            for target in targets:
                print(f"  {target}")
        else:
            print("No targets found")

    def show_error(self, error: str, details: str | None = None) -> None:
        """Show error in plain text."""
        print(f"ERROR: {error}", file=sys.stderr)
        if details:
            print(details, file=sys.stderr)

    def finalize_output(self, result: CLIResult) -> None:
        """Finalize plain output."""
        # Plain output is already sent, no finalization needed
        pass

    def needs_silent_compilation(self) -> bool:
        """Plain format requires silent compilation."""
        return True
