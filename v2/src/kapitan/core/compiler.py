"""Compilation simulation for Kapitan v2."""

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from kapitan.legacy import LegacyInventoryReader


class CompilationStatus(str, Enum):
    """Compilation status for individual targets."""
    PENDING = "pending"
    COMPILING = "compiling"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CompilationTarget:
    """Represents a compilation target."""
    name: str
    status: CompilationStatus = CompilationStatus.PENDING
    progress: float = 0.0
    duration: float = 0.0
    error_message: Optional[str] = None


class CompilationSimulator:
    """Simulates parallel compilation processes with realistic timing and status updates."""
    
    def __init__(self, console: Console, parallel_jobs: int = 4, silent: bool = False, output_path: str = "compiled", inventory_path: str = "inventory"):
        self.console = console
        self.parallel_jobs = parallel_jobs
        self.silent = silent
        self.output_path = output_path
        self.inventory_path = inventory_path
        self.targets: List[CompilationTarget] = []
        self.completed_count = 0
        self.failed_count = 0
        self.phase_timings: Dict[str, float] = {}
        
    def create_mock_targets(self, num_targets: int = 20) -> List[CompilationTarget]:
        """Create mock compilation targets with varied complexity."""
        target_types = [
            ("webapp-frontend", "js", 1.0),
            ("webapp-backend", "py", 1.5), 
            ("database", "sql", 0.8),
            ("redis-cache", "conf", 0.3),
            ("nginx-proxy", "conf", 0.4),
            ("api-gateway", "yaml", 0.6),
            ("auth-service", "go", 2.0),
            ("user-service", "py", 1.2),
            ("payment-service", "java", 2.5),
            ("notification-service", "py", 0.9),
            ("monitoring", "yaml", 0.7),
            ("logging", "yaml", 0.5),
            ("secrets", "yaml", 0.2),
            ("configmap", "yaml", 0.3),
            ("ingress", "yaml", 0.4),
            ("service-mesh", "yaml", 1.1),
            ("backup-job", "py", 0.8),
            ("migration-job", "sql", 1.3),
            ("worker-queue", "py", 1.0),
            ("analytics", "py", 1.8),
        ]
        
        targets = []
        for i in range(min(num_targets, len(target_types))):
            name, lang, base_time = target_types[i]
            # Add some randomness to compilation times
            duration = base_time + random.uniform(-0.3, 0.5)
            targets.append(CompilationTarget(name=name, duration=max(0.1, duration)))
            
        return targets
    
    def read_inventory(self, targets: Optional[List[str]] = None) -> Dict[str, any]:
        """Read inventory using legacy Kapitan system."""
        start_time = time.time()
        
        # Initialize legacy inventory reader
        legacy_reader = LegacyInventoryReader(self.inventory_path)
        
        if not self.silent:
            from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("Reading inventory...", total=None)
                
                # Check if inventory exists
                if not legacy_reader.check_inventory_exists():
                    progress.update(task, description="[yellow]No inventory found, using mock data[/yellow]")
                    time.sleep(0.5)
                    inventory_result = self._create_mock_inventory_result(targets, start_time)
                    duration = time.time() - start_time
                    progress.update(task, description=f"[green]Mock inventory loaded[/green] - {len(self.targets)} targets found in {duration:.1f}s")
                    time.sleep(0.3)
                else:
                    # Read real inventory
                    progress.update(task, description="Reading inventory structure...")
                    time.sleep(0.5)
                    
                    progress.update(task, description="Loading target definitions...")
                    time.sleep(0.7)
                    
                    progress.update(task, description="Processing classes...")
                    inventory_result = legacy_reader.read_targets(targets)
                    
                    if inventory_result["success"]:
                        # Convert legacy targets to our format
                        self._convert_legacy_targets(inventory_result["targets"])
                    else:
                        # Fallback to mock data
                        inventory_result = self._create_mock_inventory_result(targets, start_time)
                    
                    duration = time.time() - start_time
                    backend = inventory_result.get("backend", "unknown")
                    progress.update(task, description=f"[green]Inventory loaded[/green] - {len(self.targets)} targets found in {duration:.1f}s ({backend})")
                    time.sleep(0.3)
        else:
            # Silent mode
            if not legacy_reader.check_inventory_exists():
                inventory_result = self._create_mock_inventory_result(targets, start_time)
            else:
                inventory_result = legacy_reader.read_targets(targets)
                if inventory_result["success"]:
                    self._convert_legacy_targets(inventory_result["targets"])
                else:
                    inventory_result = self._create_mock_inventory_result(targets, start_time)
        
        self.phase_timings["inventory_reading"] = time.time() - start_time
        
        return {
            "targets_found": len(self.targets),
            "inventory_path": self.inventory_path,
            "duration": self.phase_timings["inventory_reading"],
            "backend": inventory_result.get("backend", "unknown"),
            "legacy_success": inventory_result.get("success", False)
        }
    
    def _convert_legacy_targets(self, legacy_targets: List[Dict]):
        """Convert legacy target format to compilation targets."""
        self.targets = []
        for target_info in legacy_targets:
            # Create compilation target with realistic timing based on target complexity
            base_time = 1.0
            
            # Adjust time based on target characteristics
            if len(target_info.get("applications", [])) > 2:
                base_time += 0.5
            if len(target_info.get("classes", [])) > 3:
                base_time += 0.3
            if target_info.get("type") in ["jsonnet", "helm"]:
                base_time += 0.7
            
            # Add some randomness
            duration = base_time + random.uniform(-0.3, 0.5)
            duration = max(0.1, duration)
            
            compilation_target = CompilationTarget(
                name=target_info["name"],
                duration=duration
            )
            self.targets.append(compilation_target)
    
    def _create_mock_inventory_result(self, targets: Optional[List[str]], start_time: float) -> Dict:
        """Create mock inventory result when legacy system fails."""
        # Create mock targets as before
        all_targets = self.create_mock_targets()
        
        # Filter targets if specific ones requested
        if targets and targets != ["all"]:
            self.targets = [t for t in all_targets if t.name in targets]
        else:
            self.targets = all_targets
        
        return {
            "success": True,
            "targets": [{"name": t.name, "type": "mock", "classes": [], "applications": []} for t in self.targets],
            "targets_found": len(self.targets),
            "backend": "mock",
            "duration": time.time() - start_time
        }
        
    def compile_target(self, target: CompilationTarget, progress: Optional[Progress], task_id: Optional[TaskID]) -> None:
        """Simulate compilation of a single target."""
        try:
            start_time = time.time()
            
            # Phase 1: Compiling (70% of total time)
            target.status = CompilationStatus.COMPILING
            compile_time = target.duration * 0.7
            compile_steps = 20
            
            for step in range(compile_steps):
                time.sleep(compile_time / compile_steps)
                target.progress = (step / compile_steps) * 70
                if progress and task_id is not None:
                    progress.update(task_id, completed=target.progress)
                
            # Phase 2: Verifying (30% of total time)
            target.status = CompilationStatus.VERIFYING
            verify_time = target.duration * 0.3
            verify_steps = 10
            
            for step in range(verify_steps):
                time.sleep(verify_time / verify_steps)
                target.progress = 70 + (step / verify_steps) * 30
                if progress and task_id is not None:
                    progress.update(task_id, completed=target.progress)
            
            # Small chance of failure (5%)
            if random.random() < 0.05:
                target.status = CompilationStatus.FAILED
                target.error_message = random.choice([
                    "Template validation failed",
                    "Missing dependency",
                    "Configuration error",
                    "Resource conflict"
                ])
                self.failed_count += 1
            else:
                target.status = CompilationStatus.COMPLETED
                target.progress = 100.0
                self.completed_count += 1
                
            target.duration = time.time() - start_time
            if progress and task_id is not None:
                progress.update(task_id, completed=target.progress)
            
        except Exception as e:
            target.status = CompilationStatus.FAILED
            target.error_message = str(e)
            self.failed_count += 1
            if progress and task_id is not None:
                progress.update(task_id, completed=0)
    
    def create_progress_display(self) -> tuple[Progress, Live]:
        """Create the progress display with individual target tracking."""
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            SpinnerColumn(),
            BarColumn(bar_width=20),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.fields[status]}"),
            TimeElapsedColumn(),
            TextColumn("→"),
            TextColumn("[dim]{task.fields[output_path]}[/dim]"),
            console=self.console,
        )
        
        # Create a live display that combines progress and summary
        live = Live(
            self.create_combined_display(progress),
            console=self.console,
            refresh_per_second=4
        )
        
        return progress, live
    
    def create_combined_display(self, progress: Progress) -> Table:
        """Create a combined display with progress and inline summary."""
        total_targets = len(self.targets)
        in_progress = total_targets - self.completed_count - self.failed_count
        
        # Create inline summary string
        summary_text = f"[cyan]Targets:[/cyan] {total_targets} | [green]Completed:[/green] {self.completed_count} | [yellow]In Progress:[/yellow] {in_progress} | [red]Failed:[/red] {self.failed_count} | [blue]Jobs:[/blue] {self.parallel_jobs}"
        
        # Main table container
        main_table = Table.grid()
        main_table.add_column()
        
        main_table.add_row(summary_text)
        main_table.add_row("")
        main_table.add_row(progress)
        
        return main_table
    
    def get_status_display(self, status: CompilationStatus) -> str:
        """Get colored status display string."""
        status_colors = {
            CompilationStatus.PENDING: "[dim]pending[/dim]",
            CompilationStatus.COMPILING: "[yellow]compiling[/yellow]",
            CompilationStatus.VERIFYING: "[blue]verifying[/blue]", 
            CompilationStatus.COMPLETED: "[green]completed[/green]",
            CompilationStatus.FAILED: "[red]failed[/red]",
        }
        return status_colors.get(status, str(status))
    
    def finalize_compilation(self) -> Dict[str, any]:
        """Simulate finalizing phase after compilation."""
        start_time = time.time()
        
        if not self.silent:
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task("Finalizing compilation...", total=None)
                
                # Simulate finalization tasks
                steps = ["Writing manifests", "Generating docs", "Creating archive", "Cleaning up"]
                for i, step in enumerate(steps):
                    progress.update(task, description=f"[yellow]{step}...[/yellow]")
                    time.sleep(random.uniform(0.2, 0.5))
                
                progress.update(task, description="[green]Compilation finalized[/green]")
                time.sleep(0.2)  # Brief pause to show completion
        else:
            # Silent mode - just simulate the work
            finalize_time = random.uniform(1.0, 2.0)
            time.sleep(finalize_time)
        
        self.phase_timings["finalizing"] = time.time() - start_time
        
        return {
            "manifests_written": len(self.targets),
            "output_directory": self.output_path,
            "duration": self.phase_timings["finalizing"]
        }
    
    def run_compilation(self, targets: Optional[List[str]] = None) -> dict:
        """Run the complete compilation simulation with all phases."""
        overall_start_time = time.time()
        
        # Phase 1: Read inventory
        inventory_result = self.read_inventory(targets)
        
        if not self.targets:
            return {
                "success": False,
                "message": "No targets found to compile",
                "completed": 0,
                "failed": 0,
                "total": 0,
                "inventory_result": inventory_result,
                "phase_timings": self.phase_timings,
                "total_duration": time.time() - overall_start_time
            }
        
        # Phase 2: Compilation
        compilation_start_time = time.time()
        
        # Create progress display only if not silent
        if not self.silent:
            progress, live = self.create_progress_display()
            
            # Create progress tasks for each target
            task_ids = {}
            for i, target in enumerate(self.targets):
                output_file_path = f"{self.output_path}/{target.name}"
                task_id = progress.add_task(
                    description=target.name,
                    total=100,
                    status=self.get_status_display(target.status),
                    output_path=output_file_path
                )
                task_ids[i] = task_id
        else:
            progress = None
            live = None
            task_ids = {}
        
        # Start live display or run silently
        context_manager = live if not self.silent else None
        
        def run_compilation():
            # Run compilation with thread pool
            with ThreadPoolExecutor(max_workers=self.parallel_jobs) as executor:
                # Submit all compilation tasks
                futures = []
                for i, target in enumerate(self.targets):
                    task_id = task_ids.get(i) if progress else None
                    future = executor.submit(
                        self.compile_target, 
                        target, 
                        progress, 
                        task_id
                    )
                    futures.append((future, i))
                
                if not self.silent:
                    # Monitor progress and update display
                    while any(not future.done() for future, _ in futures):
                        # Update status display for all targets
                        for i, target in enumerate(self.targets):
                            if progress:
                                progress.update(
                                    task_ids[i],
                                    status=self.get_status_display(target.status)
                                )
                        
                        # Update the combined display
                        if live:
                            live.update(self.create_combined_display(progress))
                        time.sleep(0.1)
                    
                    # Final update
                    for i, target in enumerate(self.targets):
                        if progress:
                            progress.update(
                                task_ids[i],
                                status=self.get_status_display(target.status)
                            )
                    if live:
                        live.update(self.create_combined_display(progress))
                else:
                    # Silent mode - just wait for completion
                    while any(not future.done() for future, _ in futures):
                        time.sleep(0.1)
        
        if context_manager:
            with context_manager:
                # Update the display to show initial state
                if live:
                    live.update(self.create_combined_display(progress))
                run_compilation()
        else:
            run_compilation()
        
        self.phase_timings["compilation"] = time.time() - compilation_start_time
        
        # Phase 3: Finalize
        finalize_result = self.finalize_compilation()
        
        # Calculate total duration
        total_duration = time.time() - overall_start_time
        
        # Return comprehensive results
        return {
            "success": self.failed_count == 0,
            "message": f"Compiled {self.completed_count}/{len(self.targets)} targets successfully",
            "completed": self.completed_count,
            "failed": self.failed_count,
            "total": len(self.targets),
            "inventory_result": inventory_result,
            "finalize_result": finalize_result,
            "phase_timings": self.phase_timings,
            "total_duration": round(total_duration, 2),
            "output_directory": self.output_path,
            "targets": [
                {
                    "name": target.name,
                    "status": target.status.value,
                    "duration": round(target.duration, 2),
                    "error": target.error_message,
                    "output_path": f"{self.output_path}/{target.name}"
                }
                for target in self.targets
            ]
        }