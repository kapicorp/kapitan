"""Inventory browsing command."""

import logging

import typer

from skipper.core.decorators import log_execution
from skipper.core.inventory_tui import show_interactive_inventory
from .base import CommandBase, command_with_config, common_error_handler

logger = logging.getLogger(__name__)


class InventoryCommand(CommandBase):
    """Handles inventory browsing functionality."""

    @common_error_handler(Exception, default_message="Failed to browse inventory")
    @log_execution("inventory_browsing", log_args=True)
    @command_with_config
    def browse_inventory(
        self,
        inventory_path: str | None = None,
        target: str | None = None,
        interactive: bool = True,
    ) -> None:
        """Browse inventory targets interactively."""
        config = self.get_config()

        # Resolve inventory path
        inv_path = self.resolve_path(
            inventory_path,
            config.global_.inventory_path,
            "inventory path"
        )

        logger.info("Starting inventory browser")
        logger.debug(f"Inventory path: {inv_path}")
        logger.debug(f"Target filter: {target}")
        logger.debug(f"Interactive mode: {interactive}")

        # Show interactive inventory
        if interactive:
            show_interactive_inventory(self.console, inv_path)
        else:
            # For non-interactive mode, show target information
            console = self.console
            console.print("[yellow]Non-interactive inventory mode[/yellow]")
            console.print(f"Inventory path: [cyan]{inv_path}[/cyan]")
            if target:
                console.print(f"Target filter: [cyan]{target}[/cyan]")
            console.print("[dim]Use --interactive for full TUI experience[/dim]")


# Create command instance
_inventory_cmd = InventoryCommand()

# Typer command function
def inventory_command(
    inventory_path: str | None = typer.Option(
        None,
        "--inventory-path",
        "-i",
        help="Path to inventory directory (overrides config)",
    ),
    target: str | None = typer.Option(
        None,
        "--target",
        "-t",
        help="Target name to show inventory for (non-interactive mode)",
    ),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Use interactive mode (default) or output mode",
    ),
) -> None:
    """Browse inventory targets interactively."""
    _inventory_cmd.browse_inventory(inventory_path, target, interactive)
