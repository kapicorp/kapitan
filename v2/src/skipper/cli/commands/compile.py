"""Compile command."""

import logging

import typer
from rich.console import Console

from ...core.compiler import KapitanCompiler
from ...core.decorators import log_execution
from ...core.exceptions import KapitanError
from ...core.models import CLIResult
from .base import CommandBase, command_with_config, common_error_handler

logger = logging.getLogger(__name__)


class CompileCommand(CommandBase):
    """Handles compilation functionality."""

    @common_error_handler(KapitanError, reraise=False, exit_code=1)
    @common_error_handler(Exception, default_message="Compilation failed")
    @log_execution("compilation", log_args=True)
    @command_with_config
    def compile_targets(
        self,
        target_patterns: list[str] | None = None,
        inventory_path: str | None = None,
        output_path: str | None = None,
        targets: list[str] | None = None,
    ) -> None:
        """Compile configuration for targets."""
        config = self.get_config()
        formatter = self.create_formatter(config)

        # Resolve paths
        inv_path = self.resolve_path(
            inventory_path,
            config.global_.inventory_path,
            "inventory path"
        )
        out_path = output_path or config.global_.output_path

        # Resolve targets from positional args or -t option
        from ...core.targets import TargetResolver

        resolver = TargetResolver(inv_path)

        # Combine positional and option targets
        all_target_patterns = []
        if target_patterns:
            all_target_patterns.extend(target_patterns)
        if targets:
            for target in targets:
                # Split comma-separated values
                all_target_patterns.extend([t.strip() for t in target.split(",") if t.strip()])

        # Resolve patterns to actual target names
        target_list = resolver.resolve_targets(all_target_patterns)

        logger.info("Starting compilation")
        logger.debug(f"Inventory path: {inv_path}")
        logger.debug(f"Output path: {out_path}")
        logger.debug(f"Targets: {', '.join(target_list)}")
        logger.debug(f"Parallel jobs: {config.global_.parallel_jobs}")

        # Create formatter and show compilation start info
        if config.global_.verbose:
            formatter.show_configuration()
        formatter.show_compilation_start(inv_path, out_path, target_list, config.global_.parallel_jobs)

        # Run compilation with appropriate mode based on formatter
        if formatter.needs_silent_compilation():
            compiler = KapitanCompiler(Console(file=None), parallel_jobs=config.global_.parallel_jobs, silent=True, output_path=out_path, inventory_path=inv_path)
        else:
            compiler = KapitanCompiler(self.console, parallel_jobs=config.global_.parallel_jobs, output_path=out_path, inventory_path=inv_path)

        compilation_result = compiler.run_compilation(target_list)

        # Show results using formatter
        formatter.show_compilation_result(compilation_result)

        # Finalize output
        result = CLIResult(
            success=compilation_result.success,
            data=compilation_result.__dict__
        )
        formatter.finalize_output(result)

        if compilation_result.success:
            logger.info("Compilation completed successfully")
        else:
            logger.error(f"Compilation failed: {compilation_result.failed} targets failed")
            raise typer.Exit(1)


# Create command instance
_compile_cmd = CompileCommand()

# Typer command function
def compile_command(
    target_patterns: list[str] | None = typer.Argument(
        None,
        help="Target names, paths, or patterns to compile (e.g., 'infra/*', 'gcp/project', 'webapp-frontend')"
    ),
    inventory_path: str | None = typer.Option(
        None,
        "--inventory-path",
        "-i",
        help="Path to inventory directory (overrides config)",
    ),
    output_path: str | None = typer.Option(
        None,
        "--output-path",
        "-o",
        help="Path to output directory (overrides config)",
    ),
    targets: list[str] | None = typer.Option(
        None,
        "--targets",
        "-t",
        help="Target names to compile (alternative to positional arguments)",
    ),
) -> None:
    """Compile configuration for targets."""
    _compile_cmd.compile_targets(target_patterns, inventory_path, output_path, targets)
