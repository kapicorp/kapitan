"""Init command for creating new Kapitan projects."""

import logging

import typer

from skipper.core.decorators import log_execution
from .base import CommandBase, common_error_handler

logger = logging.getLogger(__name__)


class InitCommand(CommandBase):
    """Handles project initialization functionality."""

    @common_error_handler(Exception, default_message="Failed to initialize project")
    @log_execution("project_initialization", log_args=True)
    def initialize_project(
        self,
        project_name: str | None = None,
        template: str = "basic",
        force: bool = False,
    ) -> None:
        """Initialize a new Kapitan project."""
        config = self.get_config()
        formatter = self.create_formatter(config)

        logger.info("Starting project initialization")
        logger.debug(f"Project name: {project_name}")
        logger.debug(f"Template: {template}")
        logger.debug(f"Force: {force}")

        # Show initialization start
        if project_name:
            self.console.print(f"[bold green]Initializing Kapitan project:[/bold green] {project_name}")
        else:
            self.console.print("[bold green]Initializing Kapitan project in current directory[/bold green]")

        # TODO: Implement actual project initialization logic
        self.console.print("[yellow]⚠️  Project initialization not yet implemented in v2[/yellow]")
        self.console.print("This command will create:")
        self.console.print("  • inventory/ directory structure")
        self.console.print("  • components/ directory")
        self.console.print("  • kapitan.toml configuration file")
        self.console.print("  • Example targets and classes")

        formatter.show_error("Not implemented", "Project initialization will be implemented in a future version")
        raise typer.Exit(1)


# Create command instance
_init_cmd = InitCommand()

# Typer command function
def init_command(
    project_name: str | None = typer.Argument(
        None,
        help="Name of the project to initialize"
    ),
    template: str = typer.Option(
        "basic",
        "--template",
        help="Template to use for initialization",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force initialization even if directory is not empty",
    ),
) -> None:
    """Initialize a new Kapitan project."""
    _init_cmd.initialize_project(project_name, template, force)
