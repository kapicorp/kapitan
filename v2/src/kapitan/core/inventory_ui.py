"""Interactive inventory viewer with console UI."""

import json
import logging
from typing import Dict, List, Optional

from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.json import JSON
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.syntax import Syntax

from kapitan.legacy import LegacyInventoryReader

logger = logging.getLogger(__name__)


class InteractiveInventoryViewer:
    """Interactive console UI for browsing inventory targets."""
    
    def __init__(self, console: Console, inventory_path: str = "inventory"):
        self.console = console
        self.inventory_path = inventory_path
        self.reader = LegacyInventoryReader(inventory_path)
        self.targets = []
        self.selected_index = 0
        self.selected_target = None
        
    def load_targets(self) -> bool:
        """Load targets from inventory."""
        try:
            result = self.reader.read_targets()
            if result["success"] and result["targets_found"] > 0:
                self.targets = result["targets"]
                self.selected_target = self.targets[0] if self.targets else None
                logger.info(f"Loaded {len(self.targets)} targets from inventory")
                return True
            else:
                logger.warning("No targets found in inventory")
                return False
        except Exception as e:
            logger.error(f"Failed to load targets: {e}")
            return False
    
    def create_layout(self) -> Layout:
        """Create the main layout with left panel (targets) and right panel (details)."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="targets", ratio=1),
            Layout(name="details", ratio=2)
        )
        
        return layout
    
    def create_header(self) -> Panel:
        """Create the header panel."""
        title = f"[bold blue]Kapitan Inventory Viewer[/bold blue] - {self.inventory_path}"
        subtitle = f"[dim]{len(self.targets)} targets loaded[/dim]" if self.targets else "[dim]No targets[/dim]"
        return Panel(
            f"{title}\n{subtitle}",
            style="cyan"
        )
    
    def create_footer(self) -> Panel:
        """Create the footer with instructions."""
        instructions = "[bold]↑/↓[/bold] Navigate | [bold]q[/bold] Quit | [bold]r[/bold] Refresh"
        return Panel(
            instructions,
            style="dim"
        )
    
    def create_targets_panel(self) -> Panel:
        """Create the left panel with target list."""
        if not self.targets:
            return Panel(
                "[dim]No targets found[/dim]",
                title="[bold]Targets[/bold]",
                border_style="blue"
            )
        
        table = Table.grid(padding=(0, 1))
        table.add_column(style="cyan")
        
        for i, target in enumerate(self.targets):
            name = target.get("name", "unknown")
            target_type = target.get("type", "unknown")
            classes_count = len(target.get("classes", []))
            apps_count = len(target.get("applications", []))
            
            # Highlight selected target
            style = "bold white on blue" if i == self.selected_index else ""
            
            # Create target display with type and counts
            display = f"{name}"
            details = f"[dim]{target_type}"
            if classes_count > 0:
                details += f" | {classes_count} classes"
            if apps_count > 0:
                details += f" | {apps_count} apps"
            details += "[/dim]"
            
            if i == self.selected_index:
                table.add_row(f"► [bold]{display}[/bold]\n  {details}", style=style)
            else:
                table.add_row(f"  {display}\n  {details}")
        
        return Panel(
            table,
            title="[bold]Targets[/bold]",
            border_style="blue"
        )
    
    def create_details_panel(self) -> Panel:
        """Create the right panel with target details."""
        if not self.selected_target:
            return Panel(
                "[dim]Select a target to view details[/dim]",
                title="[bold]Target Details[/bold]",
                border_style="green"
            )
        
        # Create a comprehensive target info dictionary
        target_info = {
            "name": self.selected_target.get("name", "unknown"),
            "type": self.selected_target.get("type", "unknown"),
            "classes": self.selected_target.get("classes", []),
            "applications": self.selected_target.get("applications", []),
            "parameters": self.selected_target.get("parameters", {}),
            "compile_targets": self.selected_target.get("compile_targets", [])
        }
        
        # Pretty print as JSON
        json_text = json.dumps(target_info, indent=2, sort_keys=True)
        
        # Use Rich JSON for syntax highlighting
        try:
            json_renderable = JSON(json_text, indent=2)
        except:
            # Fallback to syntax highlighting if JSON fails
            json_renderable = Syntax(json_text, "json", theme="monokai", line_numbers=True)
        
        target_name = self.selected_target.get("name", "unknown")
        return Panel(
            json_renderable,
            title=f"[bold]Target Details: {target_name}[/bold]",
            border_style="green",
            padding=(1, 2)
        )
    
    def update_layout(self, layout: Layout) -> None:
        """Update the layout with current data."""
        layout["header"].update(self.create_header())
        layout["footer"].update(self.create_footer())
        layout["targets"].update(self.create_targets_panel())
        layout["details"].update(self.create_details_panel())
    
    def navigate_up(self) -> bool:
        """Navigate to previous target."""
        if self.targets and self.selected_index > 0:
            self.selected_index -= 1
            self.selected_target = self.targets[self.selected_index]
            return True
        return False
    
    def navigate_down(self) -> bool:
        """Navigate to next target."""
        if self.targets and self.selected_index < len(self.targets) - 1:
            self.selected_index += 1
            self.selected_target = self.targets[self.selected_index]
            return True
        return False
    
    def refresh(self) -> bool:
        """Refresh the target list."""
        old_selected_name = None
        if self.selected_target:
            old_selected_name = self.selected_target.get("name")
        
        success = self.load_targets()
        
        # Try to restore selection
        if success and old_selected_name and self.targets:
            for i, target in enumerate(self.targets):
                if target.get("name") == old_selected_name:
                    self.selected_index = i
                    self.selected_target = target
                    break
        
        return success
    
    def run_interactive(self) -> None:
        """Run the interactive inventory viewer."""
        if not self.load_targets():
            self.console.print("[red]Failed to load inventory targets[/red]")
            return
        
        # Show all targets in a simple browsable format
        self.console.print(f"\n[bold blue]Inventory Browser[/bold blue] - {self.inventory_path}")
        self.console.print(f"[dim]Found {len(self.targets)} targets[/dim]\n")
        
        if not self.targets:
            self.console.print("[yellow]No targets found in inventory[/yellow]")
            return
        
        # Show targets overview first
        targets_table = Table(title="Available Targets")
        targets_table.add_column("#", style="dim", width=3)
        targets_table.add_column("Name", style="cyan", no_wrap=True)
        targets_table.add_column("Type", style="magenta")
        targets_table.add_column("Classes", style="blue")
        targets_table.add_column("Apps", style="green")
        
        for i, target in enumerate(self.targets, 1):
            name = target.get("name", "unknown")
            target_type = target.get("type", "unknown")
            classes_count = len(target.get("classes", []))
            apps_count = len(target.get("applications", []))
            
            targets_table.add_row(
                str(i),
                name,
                target_type,
                str(classes_count),
                str(apps_count)
            )
        
        self.console.print(targets_table)
        
        # Interactive browsing loop
        while True:
            self.console.print(f"\n[dim]Enter target number (1-{len(self.targets)}), 'q' to quit, or 'all' to see all:[/dim]")
            try:
                user_input = input("> ").strip().lower()
                
                if user_input == 'q':
                    break
                elif user_input == 'all':
                    self._show_all_targets()
                elif user_input.isdigit():
                    index = int(user_input) - 1
                    if 0 <= index < len(self.targets):
                        self._show_target_details(self.targets[index])
                    else:
                        self.console.print(f"[red]Invalid number. Please enter 1-{len(self.targets)}[/red]")
                elif user_input in [target.get("name", "").lower() for target in self.targets]:
                    # Allow searching by name
                    for target in self.targets:
                        if target.get("name", "").lower() == user_input:
                            self._show_target_details(target)
                            break
                else:
                    self.console.print("[yellow]Invalid input. Try a number, target name, 'all', or 'q'[/yellow]")
                    
            except (KeyboardInterrupt, EOFError):
                break
        
        self.console.print("\n[dim]Goodbye![/dim]")
    
    def _show_target_details(self, target: Dict) -> None:
        """Show detailed JSON information for a specific target."""
        self.console.print(f"\n[bold cyan]Target Details: {target.get('name', 'unknown')}[/bold cyan]")
        
        # Create a comprehensive target info dictionary
        target_info = {
            "name": target.get("name", "unknown"),
            "type": target.get("type", "unknown"),
            "classes": target.get("classes", []),
            "applications": target.get("applications", []),
            "parameters": target.get("parameters", {}),
            "compile_targets": target.get("compile_targets", [])
        }
        
        # Pretty print as JSON with Rich
        try:
            json_text = json.dumps(target_info, indent=2, sort_keys=True)
            json_renderable = JSON(json_text, indent=2)
            self.console.print(json_renderable)
        except Exception:
            # Fallback to syntax highlighting if JSON fails
            json_text = json.dumps(target_info, indent=2, sort_keys=True)
            json_renderable = Syntax(json_text, "json", theme="monokai", line_numbers=True)
            self.console.print(json_renderable)
    
    def _show_all_targets(self) -> None:
        """Show detailed JSON information for all targets."""
        self.console.print(f"\n[bold cyan]All Targets ({len(self.targets)} total)[/bold cyan]")
        
        all_targets = []
        for target in self.targets:
            target_info = {
                "name": target.get("name", "unknown"),
                "type": target.get("type", "unknown"),
                "classes": target.get("classes", []),
                "applications": target.get("applications", []),
                "parameters": target.get("parameters", {}),
                "compile_targets": target.get("compile_targets", [])
            }
            all_targets.append(target_info)
        
        # Pretty print all targets as JSON
        try:
            json_text = json.dumps(all_targets, indent=2, sort_keys=True)
            json_renderable = JSON(json_text, indent=2)
            self.console.print(json_renderable)
        except Exception:
            # Fallback to syntax highlighting if JSON fails
            json_text = json.dumps(all_targets, indent=2, sort_keys=True)
            json_renderable = Syntax(json_text, "json", theme="monokai", line_numbers=True)
            self.console.print(json_renderable)
    
    def _run_with_keyboard(self, layout: Layout, live: Live) -> None:
        """Run interactive mode with keyboard support."""
        import keyboard
        
        while True:
            try:
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    if event.name == 'q':
                        break
                    elif event.name == 'up':
                        if self.navigate_up():
                            self.update_layout(layout)
                    elif event.name == 'down':
                        if self.navigate_down():
                            self.update_layout(layout)
                    elif event.name == 'r':
                        if self.refresh():
                            self.update_layout(layout)
            except KeyboardInterrupt:
                break
    
    def _run_simple_mode(self, layout: Layout, live: Live) -> None:
        """Run simple mode without keyboard events."""
        self.console.print("[dim]Simple mode - press Enter to cycle through targets, 'q' + Enter to quit[/dim]")
        
        while True:
            try:
                user_input = input().strip().lower()
                if user_input == 'q':
                    break
                elif user_input == 'r':
                    if self.refresh():
                        self.update_layout(layout)
                else:
                    # Cycle through targets
                    if not self.navigate_down():
                        self.selected_index = 0
                        if self.targets:
                            self.selected_target = self.targets[0]
                    self.update_layout(layout)
            except KeyboardInterrupt:
                break
            except EOFError:
                break


def show_interactive_inventory(console: Console, inventory_path: str = "inventory") -> None:
    """Show the interactive inventory viewer."""
    viewer = InteractiveInventoryViewer(console, inventory_path)
    viewer.run_interactive()