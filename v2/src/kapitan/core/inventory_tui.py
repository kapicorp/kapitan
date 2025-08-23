"""Advanced TUI for interactive inventory browsing with keyboard navigation and JSONPath search."""

import json
import logging
from typing import Any, Dict, List, Optional

import yaml

import jsonpath_ng
from jsonpath_ng import parse as jsonpath_parse
from rich.syntax import Syntax
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Input, Static, TextArea
from textual.worker import get_current_worker

from kapitan.legacy import LegacyInventoryReader

logger = logging.getLogger(__name__)


class JSONPathCompleter:
    """Auto-completion for JSONPath expressions."""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self._extract_paths()
    
    def _extract_paths(self) -> None:
        """Extract all possible JSONPath expressions from the data."""
        self.paths = set()
        self._extract_from_value("", self.data)
    
    def _extract_from_value(self, prefix: str, value: Any, max_depth: int = 5) -> None:
        """Recursively extract paths from a value."""
        if max_depth <= 0:
            return
            
        if isinstance(value, dict):
            for key, val in value.items():
                path = f"{prefix}.{key}" if prefix else key
                self.paths.add(f"$.{path}")
                self._extract_from_value(path, val, max_depth - 1)
        elif isinstance(value, list) and value:
            # Add array syntax
            self.paths.add(f"$.{prefix}[*]" if prefix else "$[*]")
            if len(value) > 0:
                self._extract_from_value(f"{prefix}[0]" if prefix else "[0]", value[0], max_depth - 1)
    
    def get_completions(self, current_text: str) -> List[str]:
        """Get completion suggestions for the current text."""
        if not current_text:
            return sorted(list(self.paths))[:10]
        
        # Find matches
        matches = []
        lower_text = current_text.lower()
        
        for path in self.paths:
            if lower_text in path.lower():
                matches.append(path)
        
        # Sort by relevance (exact matches first, then starts with, then contains)
        exact_matches = [p for p in matches if p.lower() == lower_text]
        starts_with = [p for p in matches if p.lower().startswith(lower_text) and p not in exact_matches]
        contains = [p for p in matches if p not in exact_matches and p not in starts_with]
        
        return sorted(exact_matches) + sorted(starts_with) + sorted(contains)[:10]


class TargetList(DataTable):
    """Widget for displaying and selecting targets."""
    
    def __init__(self, targets: List[Dict], **kwargs):
        super().__init__(**kwargs)
        self.targets = targets
        self.target_map = {}  # Map row keys to targets
        self.cursor_type = "row"
        self.zebra_stripes = True
        
    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self.add_columns("")  # Empty header to save space
        self.show_header = False  # Hide the header row
        
        for i, target in enumerate(self.targets):
            name = target.get("name", "unknown")
            
            row_key = f"target_{i}"
            self.target_map[row_key] = target
            
            self.add_row(
                name,
                key=row_key
            )
        
        if self.targets:
            self.move_cursor(row=0)
    
    def get_selected_target(self) -> Optional[Dict]:
        """Get the currently selected target."""
        if self.cursor_row is None:
            return None
        
        # Get the row key from the current cursor position
        try:
            if self.cursor_row >= self.row_count:
                return None
                
            row_key = self.get_row_at(self.cursor_row).key
            target = self.target_map.get(row_key)
            return target
        except (IndexError, AttributeError):
            return None
    
    def update_targets(self, targets: List[Dict]) -> None:
        """Update the target list with new data."""
        self.targets = targets
        self.target_map.clear()
        self.clear()
        
        # Don't re-add columns - they're already added in on_mount
        
        for i, target in enumerate(targets):
            name = target.get("name", "unknown")
            
            row_key = f"target_{i}"
            self.target_map[row_key] = target
            
            self.add_row(
                name,
                key=row_key
            )
        
        if targets:
            self.move_cursor(row=0)


class JSONViewer(Container):
    """Scrollable YAML/JSON viewer with selectable text."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_widget = TextArea(
            "Loading targets...",
            read_only=True,
            show_line_numbers=True,
            language="yaml"  # Default to YAML
        )
        self.can_focus = True
        self.output_format = "yaml"  # Default to YAML
    
    def compose(self) -> ComposeResult:
        """Compose the JSON viewer."""
        yield self.content_widget
    
    def on_mount(self) -> None:
        """Set up the JSON viewer when mounted."""
        self.content_widget.can_focus = True
    
    def update_content(self, data: Dict[str, Any]) -> None:
        """Update the content in the selected format (YAML or JSON)."""
        try:
            if self.output_format == "yaml":
                # Format as YAML
                formatted = yaml.dump(data, default_flow_style=False, sort_keys=True, indent=2)
                self.content_widget.language = "yaml"
            else:
                # Format as JSON
                formatted = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
                self.content_widget.language = "json"
            
            self.content_widget.text = formatted
        except Exception as e:
            self.content_widget.text = f"Error formatting {self.output_format.upper()}: {e}"
    
    def toggle_format(self) -> str:
        """Toggle between YAML and JSON formats."""
        self.output_format = "json" if self.output_format == "yaml" else "yaml"
        return self.output_format


class JSONPathSearch(Container):
    """JSONPath search widget that searches across all targets."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.completer = None
        self.all_targets = []
        self.current_query = ""
        self.app_instance = None
        self.selected_target_name = None
        self.search_timer = None
        self.current_data = None  # Cache last good result
        self.current_suggestions = []  # Store current suggestions for Tab completion
    
    def compose(self) -> ComposeResult:
        """Compose the search widget."""
        yield Input(
            placeholder="JSONPath query (e.g., $[*].parameters.mysql.image, $..[name='target'].parameters)",
            id="jsonpath-input"
        )
        yield Static("", id="autocomplete-suggestions")
    
    def on_mount(self) -> None:
        """Set up the search widget when mounted."""
        input_widget = self.query_one("#jsonpath-input", Input)
        input_widget.can_focus = True
    
    def set_all_targets(self, targets: List[Dict[str, Any]]) -> None:
        """Set all targets for JSONPath searching."""
        self.all_targets = targets
        if targets:
            self.completer = JSONPathCompleter({"targets": targets})
        # Apply current query if we have one
        if self.current_query:
            self._apply_jsonpath_filter(self.current_query)
    
    def set_selected_target(self, target_name: str) -> None:
        """Set the selected target and update the JSONPath query."""
        self.selected_target_name = target_name
        
        # Cache the parameters as current data
        for target in self.all_targets:
            if target.get("name") == target_name:
                self.current_data = target.get("parameters", {})
                break
        
        # Default to showing parameters of the selected target
        target_query = f"$..[name='{target_name}'].parameters"
        self._update_input_value(target_query)
        self.current_query = target_query
        self._apply_jsonpath_filter(target_query)
    
    def set_app(self, app_instance) -> None:
        """Set reference to the main app for updating the JSON viewer."""
        self.app_instance = app_instance
    
    def _update_input_value(self, value: str) -> None:
        """Update the input field value programmatically."""
        try:
            input_widget = self.query_one("#jsonpath-input", Input)
            input_widget.value = value
            # Position cursor at the end to avoid auto-selection
            input_widget.cursor_position = len(value)
        except:
            pass
    
    def _apply_jsonpath_filter(self, query: str) -> None:
        """Apply JSONPath filter across all targets and update the main JSON viewer."""
        if not self.app_instance or not self.all_targets:
            return
            
        try:
            json_viewer = self.app_instance.query_one("#json-viewer", JSONViewer)
            
            if not query.strip():
                # No query - show current data or all targets
                if self.current_data:
                    json_viewer.update_content(self.current_data)
                else:
                    json_viewer.update_content({"all_targets": self.all_targets})
                return
            
            # Check for our custom target name filter syntax
            if query.startswith("$..[name='") and ("']" in query):
                # Extract target name
                start_pos = len("$..[name='")
                quote_end = query.find("']")
                if quote_end <= start_pos:
                    return  # Incomplete query, don't show error
                
                target_name = query[start_pos:quote_end]
                
                # Find the target
                target = None
                for t in self.all_targets:
                    if t.get("name") == target_name:
                        target = t
                        break
                
                if not target:
                    if self.app_instance:
                        self.app_instance.notify(f"Target '{target_name}' not found", timeout=1)
                    return
                
                # Parse the path after the target name
                remaining_path = query[quote_end + 2:]  # After ']'
                
                if not remaining_path:
                    # Just the target name - show full target
                    json_viewer.update_content(target)
                    self.current_data = target
                    return
                elif remaining_path.startswith(".parameters"):
                    # Navigate into parameters
                    param_path = remaining_path[11:]  # After '.parameters'
                    result = target.get("parameters", {})
                    
                    if param_path:
                        # Navigate deeper into parameters
                        path_parts = [p for p in param_path.split('.') if p]
                        for part in path_parts:
                            if isinstance(result, dict) and part in result:
                                result = result[part]
                            else:
                                # Path not found - show autocomplete suggestions
                                if isinstance(result, dict):
                                    available_keys = list(result.keys())
                                    # Filter suggestions based on partial input
                                    filtered_keys = self._filter_suggestions(available_keys, part)
                                    partial_path = ".parameters." + ".".join(path_parts[:path_parts.index(part)])
                                    self._show_suggestions(filtered_keys, partial_path, part)
                                return
                    
                    json_viewer.update_content(result)
                    self.current_data = result
                    # Show available keys if result is a dict
                    if isinstance(result, dict):
                        available_keys = list(result.keys())
                        current_path = remaining_path[11:] if remaining_path.startswith(".parameters") else remaining_path[1:]
                        self._show_suggestions(available_keys, f".parameters.{current_path}" if current_path else ".parameters")
                    else:
                        self._clear_suggestions()
                    return
                else:
                    # Other paths - try to navigate
                    result = target
                    if remaining_path.startswith('.'):
                        path_parts = [p for p in remaining_path[1:].split('.') if p]
                        for part in path_parts:
                            if isinstance(result, dict) and part in result:
                                result = result[part]
                            else:
                                # Path not found - show autocomplete suggestions
                                if isinstance(result, dict):
                                    available_keys = list(result.keys())
                                    # Filter suggestions based on partial input
                                    filtered_keys = self._filter_suggestions(available_keys, part)
                                    partial_path = "." + ".".join(path_parts[:path_parts.index(part)])
                                    self._show_suggestions(filtered_keys, partial_path, part)
                                return
                        
                        json_viewer.update_content(result)
                        self.current_data = result
                        # Show available keys if result is a dict
                        if isinstance(result, dict):
                            available_keys = list(result.keys())
                            self._show_suggestions(available_keys, remaining_path)
                        else:
                            self._clear_suggestions()
                        return
                
                # Fallback
                return
            
            # Parse and execute standard JSONPath query across all targets
            jsonpath_expr = jsonpath_parse(query)
            matches = jsonpath_expr.find(self.all_targets)
            
            if matches:
                result_data = [match.value for match in matches]
                if len(result_data) == 1:
                    # Single match - show the value directly
                    filtered_data = result_data[0]
                else:
                    # Multiple matches - show as array
                    filtered_data = result_data
                
                json_viewer.update_content(filtered_data)
                self.current_data = filtered_data  # Cache successful result
            else:
                # No matches found - show notification but keep current view
                if self.app_instance:
                    self.app_instance.notify(f"No matches for: {query[:20]}...", timeout=1)
                
        except Exception as e:
            # Don't show intrusive errors while typing - just notify
            if self.app_instance:
                self.app_instance.notify(f"Invalid query: {str(e)[:30]}...", timeout=1)
    
    @on(Input.Changed, "#jsonpath-input")
    def on_jsonpath_input(self, event: Input.Changed) -> None:
        """Handle JSONPath input changes with delayed search."""
        self.current_query = event.value.strip()
        
        # Cancel any existing timer
        if self.search_timer:
            self.search_timer.stop()
        
        # If query is empty, show current data immediately
        if not self.current_query:
            self._clear_suggestions()
            self.current_suggestions = []
            if self.current_data and self.app_instance:
                json_viewer = self.app_instance.query_one("#json-viewer", JSONViewer)
                json_viewer.update_content(self.current_data)
            return
        
        # Set up delayed search (500ms delay)
        self.search_timer = self.set_timer(0.5, self._delayed_search)
    
    def on_key(self, event) -> None:
        """Handle key presses for Tab autocompletion."""
        if event.key == "tab" and self.current_suggestions:
            # Get the best suggestion (first one)
            best_suggestion = self.current_suggestions[0]
            
            # Find the current partial input we're trying to complete
            input_widget = self.query_one("#jsonpath-input", Input)
            current_value = input_widget.value
            
            # Find the last incomplete part after the last dot
            if "." in current_value:
                parts = current_value.split(".")
                if parts:
                    last_part = parts[-1]
                    # Replace the partial with the full suggestion
                    new_value = ".".join(parts[:-1]) + "." + best_suggestion
                    input_widget.value = new_value
                    # Position cursor at the end
                    input_widget.cursor_position = len(new_value)
                    # Prevent the default tab behavior
                    event.prevent_default()
                    # Update the query and trigger search
                    self.current_query = new_value.strip()
                    self._apply_jsonpath_filter(self.current_query)
    
    def _delayed_search(self) -> None:
        """Perform the actual search after delay."""
        self._apply_jsonpath_filter(self.current_query)
    
    def _filter_suggestions(self, available_keys: list, partial_input: str) -> list:
        """Filter available keys based on partial input for autocompletion."""
        if not partial_input:
            return available_keys
        
        partial_lower = partial_input.lower()
        filtered = []
        
        # First, add exact matches
        exact_matches = [key for key in available_keys if key.lower() == partial_lower]
        filtered.extend(exact_matches)
        
        # Then, add keys that start with the partial input
        starts_with = [key for key in available_keys 
                      if key.lower().startswith(partial_lower) and key not in exact_matches]
        filtered.extend(starts_with)
        
        # Finally, add keys that contain the partial input
        contains = [key for key in available_keys 
                   if partial_lower in key.lower() and key not in exact_matches and key not in starts_with]
        filtered.extend(contains)
        
        return filtered[:10]  # Limit to 10 suggestions
    
    def _show_suggestions(self, suggestions: list, current_path: str = "", partial_input: str = "") -> None:
        """Show autocomplete suggestions in the suggestions area."""
        try:
            # Store suggestions for Tab completion
            self.current_suggestions = suggestions
            
            suggestions_widget = self.query_one("#autocomplete-suggestions", Static)
            if suggestions:
                # Format suggestions nicely
                if partial_input:
                    suggestion_text = f"Matches for '{partial_input}': {', '.join(suggestions[:8])} (Tab to complete)"
                elif current_path:
                    suggestion_text = f"Available after '{current_path}': {', '.join(suggestions[:8])} (Tab to complete)"
                else:
                    suggestion_text = f"Suggestions: {', '.join(suggestions[:8])} (Tab to complete)"
                suggestions_widget.update(suggestion_text)
            else:
                if partial_input:
                    suggestions_widget.update(f"No matches for '{partial_input}'")
                else:
                    suggestions_widget.update("")
        except:
            pass
    
    def _clear_suggestions(self) -> None:
        """Clear autocomplete suggestions."""
        try:
            self.current_suggestions = []
            suggestions_widget = self.query_one("#autocomplete-suggestions", Static)
            suggestions_widget.update("")
        except:
            pass


class InventoryTUIApp(App):
    """Main TUI application for inventory browsing."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    
    #left-panel {
        width: 20;  /* Default, will be updated dynamically */
        border: solid green;
        margin: 0 1 0 0;
        padding: 0;
    }
    
    #right-panel {
        width: 1fr;
        border: solid blue;
        layout: vertical;
        margin: 0 0 0 1;
        padding: 0;
    }
    
    #target-list {
        height: 1fr;
        margin: 0;
        padding: 0;
        min-width: 0;
        width: 100%;
    }
    
    #target-list DataTable {
        padding: 0;
        margin: 0;
        min-width: 0;
    }
    
    #search-panel {
        height: 5;
        border: solid yellow;
        margin: 0;
        padding: 0;
    }
    
    #json-viewer {
        height: 1fr;
        margin: 0;
        padding: 0;
        border: solid blue;
    }
    
    #json-viewer TextArea {
        height: 1fr;
        background: $surface;
        margin: 0;
        padding: 0;
        border: none;
    }
    
    #jsonpath-input {
        margin: 0;
        height: 1;
        width: 1fr;
        background: $surface;
        color: $text;
        padding: 0 1;
        border: none;
    }
    
    #autocomplete-suggestions {
        height: 2;
        margin: 0;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
        text-style: italic;
    }
    
    .panel-title {
        text-style: bold;
        background: $surface;
        padding: 0 1;
        margin: 0;
    }
    
    .placeholder {
        text-align: center;
        text-style: italic;
        color: $text-muted;
    }
    
    Header {
        height: 1;
    }
    
    Footer {
        height: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f", "focus_search", "Search"),
        Binding("v", "focus_viewer", "View"),
        Binding("t", "toggle_format", "YAML/JSON"),
        Binding("ctrl+f", "fold_all", "Fold All"),
        Binding("ctrl+u", "unfold_all", "Unfold All"),
        Binding("escape", "focus_list", "Back to List"),
        Binding("tab", "tab_complete", "Tab Complete", show=False),
    ]
    
    def __init__(self, inventory_path: str = "inventory", **kwargs):
        super().__init__(**kwargs)
        self.inventory_path = inventory_path
        self.reader = LegacyInventoryReader(inventory_path)
        self.targets = []
        self.current_target = None
    
    async def on_mount(self) -> None:
        """Load data when the app mounts."""
        self.title = f"Kapitan Inventory Browser - {self.inventory_path}"
        await self.load_targets()
    
    async def load_targets(self) -> None:
        """Load targets from inventory."""
        try:
            # Load targets from inventory
            result = self.reader.read_targets()
            if result["success"] and result["targets_found"] > 0:
                self.targets = result["targets"]
                logger.info(f"Loaded {len(self.targets)} targets from inventory")
                
                # Calculate optimal left panel width based on target names
                self._update_left_panel_width()
                
                # Update the target list with new data
                target_list = self.query_one("#target-list", TargetList)
                target_list.update_targets(self.targets)
                
                # Select the first target if available and trigger initial display
                if self.targets:
                    # Force initial content display by calling the update directly
                    self.call_after_refresh(self._show_first_target)
                
                self.notify(f"Loaded {len(self.targets)} targets successfully", severity="information")
            else:
                self.notify("No targets found in inventory", severity="warning")
        except Exception as e:
            logger.error(f"Failed to load targets: {e}")
            self.notify(f"Failed to load targets: {e}", severity="error")
    
    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        
        with Container(id="main-container"):
            with Vertical(id="left-panel"):
                yield Static("Targets", classes="panel-title")
                yield TargetList([], id="target-list")
            
            with Vertical(id="right-panel"):
                yield JSONPathSearch(id="search-panel")
                yield JSONViewer(id="json-viewer")
        
        yield Footer()
    
    @on(DataTable.RowHighlighted, "#target-list")
    def on_target_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle target row highlighting (cursor movement)."""
        target_list = self.query_one("#target-list", TargetList)
        
        # Try to get target by cursor row directly
        if event.cursor_row is not None and 0 <= event.cursor_row < len(target_list.targets):
            selected_target = target_list.targets[event.cursor_row]
            if selected_target:
                self.current_target = selected_target
                self._update_target_details(selected_target)
    
    @on(DataTable.RowSelected, "#target-list")
    def on_target_selected(self, event: DataTable.RowSelected) -> None:
        """Handle target row selection (Enter key)."""
        target_list = self.query_one("#target-list", TargetList)
        
        # Try to get target by cursor row directly
        if event.cursor_row is not None and 0 <= event.cursor_row < len(target_list.targets):
            selected_target = target_list.targets[event.cursor_row]
            if selected_target:
                self.current_target = selected_target
                self._update_target_details(selected_target)
    
    def _update_target_details(self, target: Dict[str, Any]) -> None:
        """Update the target details view and set JSONPath to filter this target."""
        try:
            # Update search panel with all targets and set selected target
            search_panel = self.query_one("#search-panel", JSONPathSearch)
            search_panel.set_app(self)  # Set reference to this app
            search_panel.set_all_targets(self.targets)
            search_panel.set_selected_target(target.get("name", "unknown"))
            
        except Exception as e:
            self.notify(f"Error updating details: {e}", severity="error")
    
    def action_refresh(self) -> None:
        """Refresh the target list."""
        self.run_worker(self.load_targets, exclusive=True)
        self.notify("Refreshing targets...")
    
    def action_focus_search(self) -> None:
        """Focus on the JSONPath search input."""
        search_input = self.query_one("#jsonpath-input", Input)
        search_input.focus()
    
    def action_focus_list(self) -> None:
        """Focus back on the target list."""
        target_list = self.query_one("#target-list", TargetList)
        target_list.focus()
    
    def action_focus_viewer(self) -> None:
        """Focus on the JSON viewer for text selection."""
        json_viewer = self.query_one("#json-viewer", JSONViewer)
        json_viewer.content_widget.focus()
    
    def action_fold_all(self) -> None:
        """Fold all JSON sections."""
        try:
            json_viewer = self.query_one("#json-viewer", JSONViewer)
            text_area = json_viewer.content_widget
            
            # Check if TextArea has folding methods
            if hasattr(text_area, 'fold_all'):
                text_area.fold_all()
                self.notify("Folded all sections", timeout=1)
            elif hasattr(text_area, 'action_fold_all'):
                text_area.action_fold_all()
                self.notify("Folded all sections", timeout=1)
            else:
                # List available methods for debugging
                methods = [m for m in dir(text_area) if 'fold' in m.lower()]
                self.notify(f"Folding methods: {methods}" if methods else "No folding methods available", timeout=3)
        except Exception as e:
            self.notify(f"Folding error: {e}", timeout=2)
    
    def action_unfold_all(self) -> None:
        """Unfold all JSON sections."""
        try:
            json_viewer = self.query_one("#json-viewer", JSONViewer)
            text_area = json_viewer.content_widget
            
            # Check if TextArea has unfolding methods
            if hasattr(text_area, 'unfold_all'):
                text_area.unfold_all()
                self.notify("Unfolded all sections", timeout=1)
            elif hasattr(text_area, 'action_unfold_all'):
                text_area.action_unfold_all()
                self.notify("Unfolded all sections", timeout=1)
            else:
                # List available methods for debugging
                methods = [m for m in dir(text_area) if 'fold' in m.lower() or 'unfold' in m.lower()]
                self.notify(f"Unfolding methods: {methods}" if methods else "No unfolding methods available", timeout=3)
        except Exception as e:
            self.notify(f"Unfolding error: {e}", timeout=2)
    
    def action_toggle_format(self) -> None:
        """Toggle between YAML and JSON output formats."""
        try:
            json_viewer = self.query_one("#json-viewer", JSONViewer)
            new_format = json_viewer.toggle_format()
            self.notify(f"Output format: {new_format.upper()}", timeout=1)
            
            # Refresh the current content in the new format
            if self.current_target:
                self._update_target_details(self.current_target)
        except Exception as e:
            self.notify(f"Toggle error: {e}", timeout=2)
    
    def action_tab_complete(self) -> None:
        """Handle Tab completion (delegated to search panel)."""
        # Tab completion is handled by the JSONPathSearch widget's on_key method
        pass
    
    def _update_left_panel_width(self) -> None:
        """Update left panel width based on longest target name."""
        if not self.targets:
            return
            
        # Find the longest target name
        max_length = max(len(target.get("name", "unknown")) for target in self.targets)
        # Add some padding for borders and selection highlighting
        optimal_width = min(max_length + 4, 30)  # Max of 30 characters
        
        # Update the CSS dynamically
        try:
            left_panel = self.query_one("#left-panel")
            left_panel.styles.width = optimal_width
            self.notify(f"Panel width: {optimal_width} (longest name: {max_length} chars)", timeout=2)
        except:
            # If panel not found yet, we'll set it in CSS initially
            pass
    
    def _show_first_target(self) -> None:
        """Show the first target's content immediately after load."""
        if self.targets:
            target_list = self.query_one("#target-list", TargetList)
            # Always select the first target by default
            target_list.move_cursor(row=0)
            first_target = self.targets[0]
            self.current_target = first_target
            self._update_target_details(first_target)
            
            # Also initialize the search panel with all targets
            try:
                search_panel = self.query_one("#search-panel", JSONPathSearch)
                search_panel.set_app(self)
                search_panel.set_all_targets(self.targets)
            except:
                pass


def run_inventory_tui(inventory_path: str = "inventory") -> None:
    """Run the TUI inventory browser."""
    app = InventoryTUIApp(inventory_path=inventory_path)
    app.run()


# For backwards compatibility with the existing interface
def show_interactive_inventory(console, inventory_path: str = "inventory") -> None:
    """Show the interactive inventory viewer (TUI version)."""
    try:
        run_inventory_tui(inventory_path)
    except Exception as e:
        console.print(f"[red]Failed to start TUI: {e}[/red]")
        console.print("[yellow]Falling back to simple interactive mode...[/yellow]")
        
        # Fall back to the old simple interface
        from kapitan.core.inventory_ui import InteractiveInventoryViewer
        viewer = InteractiveInventoryViewer(console, inventory_path)
        viewer.run_interactive()