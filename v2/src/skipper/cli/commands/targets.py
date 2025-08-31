"""Targets listing command."""

import logging

import typer

from skipper.core.decorators import log_execution
from skipper.core.inventory import get_inventory_reader
from skipper.core.models import CLIResult
from .base import CommandBase, command_with_config, common_error_handler

logger = logging.getLogger(__name__)


class TargetsCommand(CommandBase):
    """Handles targets listing functionality."""

    @common_error_handler(Exception, default_message="Failed to list targets")
    @log_execution("targets_listing", log_args=True)
    @command_with_config
    def list_targets(
        self,
        target_patterns: list[str] | None = None,
        inventory_path: str | None = None,
        verbose: bool = False,
    ) -> None:
        """List available targets from inventory."""
        config = self.get_config()
        formatter = self.create_formatter(config)

        # Resolve inventory path
        inv_path = self.resolve_path(
            inventory_path,
            config.global_.inventory_path,
            "inventory path"
        )

        if verbose:
            logger.debug(f"Configuration loaded from: {', '.join(config._sources)}")
            formatter.show_configuration()

        # Initialize inventory reader using the factory
        inventory_reader = get_inventory_reader(inv_path)
        formatter.show_inventory_start()

        # Read inventory
        inventory_result = inventory_reader.read_targets()
        formatter.show_inventory_result(inventory_result)

        if not inventory_result.success:
            formatter.show_error("Failed to read inventory", inventory_result.error)
            result = CLIResult(
                success=False,
                error="InventoryError",
                message=inventory_result.error
            )
            formatter.finalize_output(result)
            raise typer.Exit(1)

        # Filter targets if patterns were provided
        targets_to_show = inventory_result.targets
        if target_patterns:
            from skipper.core.targets import TargetResolver
            resolver = TargetResolver(inv_path)
            resolved_names = resolver.resolve_targets(target_patterns)
            targets_to_show = [t for t in inventory_result.targets if t.name in resolved_names]

        # Show targets list
        target_names = [target.name for target in targets_to_show]
        formatter.show_targets_list(target_names)

        # Create result for JSON output
        result = CLIResult(
            success=True,
            data={
                "targets": [
                    {
                        "name": target.name,
                        "type": target.type,
                        "applications": target.applications,
                        "classes": target.classes
                    }
                    for target in targets_to_show
                ],
                "count": len(targets_to_show),
                "total_available": inventory_result.targets_found,
                "inventory_path": inventory_result.inventory_path,
                "duration": inventory_result.duration,
                "backend": inventory_result.backend
            }
        )
        formatter.finalize_output(result)


# Create command instance
_targets_cmd = TargetsCommand()

# Typer command function
def targets_command(
    target_patterns: list[str] | None = typer.Argument(
        None,
        help="Target patterns to filter (e.g., 'infra/*', 'gcp/project'). If not specified, shows all targets."
    ),
    inventory_path: str | None = typer.Option(
        None,
        "--inventory-path",
        "-i",
        help="Path to inventory directory (overrides config)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose output",
    ),
) -> None:
    """List available targets from inventory."""
    _targets_cmd.list_targets(target_patterns, inventory_path, verbose)
