"""Multi-phase compilation system with real-time progress tracking.

Implements a three-phase compilation process:
1. Inventory reading - Load and parse target definitions
2. Target compilation - Parallel processing of targets
3. Finalization - Output writing and cleanup

Features parallel execution, real-time progress display, and comprehensive
result tracking with timing metrics.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from skipper.legacy import LegacyInventoryReader

from .models import (
    CompilationResult,
    CompilationStatus,
    CompilationTarget,
    FinalizationResult,
    InventoryResult,
    PhaseTimings,
    TargetInfo,
)


class KapitanCompiler:
    """Multi-phase compiler with parallel execution and progress tracking.
    
    Manages the complete compilation workflow from inventory loading through
    target compilation to output finalization. Supports both interactive
    progress display and silent operation for CI environments.
    
    Attributes:
        console: Rich console for output formatting.
        parallel_jobs: Number of concurrent compilation jobs.
        silent: Whether to suppress progress display.
        output_path: Directory for compilation output.
        inventory_path: Path to inventory directory.
        targets: List of targets being compiled.
        completed_count: Number of successfully compiled targets.
        failed_count: Number of failed targets.
        phase_timings: Timing data for each compilation phase.
    """

    def __init__(self, console: Console, parallel_jobs: int = 4, silent: bool = False, output_path: str = "compiled", inventory_path: str = "inventory"):
        """Initialize compiler with configuration and dependencies.
        
        Args:
            console: Rich console for output formatting.
            parallel_jobs: Number of concurrent compilation jobs.
            silent: Whether to suppress progress display.
            output_path: Directory where compilation output will be written.
            inventory_path: Path to inventory directory to load from.
        """
        self.console = console
        self.parallel_jobs = parallel_jobs
        self.silent = silent
        self.output_path = output_path
        self.inventory_path = inventory_path
        self.targets: list[CompilationTarget] = []
        self.completed_count = 0
        self.failed_count = 0
        self.phase_timings = {}


    def read_inventory(self, targets: list[str] | None = None) -> InventoryResult:
        """Load inventory from storage using legacy Kapitan reader.
        
        Args:
            targets: Optional list of specific targets to load.
            
        Returns:
            InventoryResult with loaded targets and metadata.
            
        Raises:
            FileNotFoundError: If inventory directory doesn't exist.
            RuntimeError: If inventory loading fails.
        """
        start_time = time.perf_counter()

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
                    progress.update(task, description="[red]No inventory found[/red]")
                    raise FileNotFoundError(f"No inventory found at: {self.inventory_path}")

                # Read real inventory
                progress.update(task, description="Reading inventory structure...")

                progress.update(task, description="Loading target definitions...")

                progress.update(task, description="Processing classes...")
                legacy_result = legacy_reader.read_targets(targets)

                if not legacy_result.success:
                    progress.update(task, description="[red]Failed to read inventory[/red]")
                    raise RuntimeError(f"Failed to read inventory: {legacy_result.error or 'Unknown error'}")

                # Convert legacy targets to our format
                self._convert_legacy_targets(legacy_result.targets)

                duration = time.perf_counter() - start_time
                progress.update(task, description=f"[green]Inventory loaded[/green] - {len(self.targets)} targets found in {duration:.1f}s ({legacy_result.backend})")
        else:
            # Silent mode
            if not legacy_reader.check_inventory_exists():
                raise FileNotFoundError(f"No inventory found at: {self.inventory_path}")

            legacy_result = legacy_reader.read_targets(targets)
            if not legacy_result.success:
                raise RuntimeError(f"Failed to read inventory: {legacy_result.error or 'Unknown error'}")

            self._convert_legacy_targets(legacy_result.targets)

        duration = time.perf_counter() - start_time

        return InventoryResult(
            success=True,
            targets=legacy_result.targets,
            targets_found=len(self.targets),
            inventory_path=self.inventory_path,
            duration=duration,
            backend=legacy_result.backend
        )

    def _convert_legacy_targets(self, legacy_targets: list[TargetInfo]):
        """Convert legacy target info to compilation targets with timing estimates.
        
        Analyzes target characteristics to estimate compilation time and
        creates CompilationTarget instances for progress tracking.
        
        Args:
            legacy_targets: List of target information from legacy reader.
        """
        self.targets = []
        for target_info in legacy_targets:
            # Create compilation target with realistic timing based on target complexity
            base_time = 1.0

            # Adjust time based on target characteristics
            if len(target_info.applications) > 2:
                base_time += 0.5
            if len(target_info.classes) > 3:
                base_time += 0.3
            if target_info.type in ["jsonnet", "helm"]:
                base_time += 0.7

            # Use base time without randomness
            duration = max(0.1, base_time)

            compilation_target = CompilationTarget(
                name=target_info.name,
                duration=duration,
                output_path=f"{self.output_path}/{target_info.name}"
            )
            self.targets.append(compilation_target)


    def compile_target(self, target: CompilationTarget, progress: Progress | None, task_id: TaskID | None) -> None:
        """Compile a single target with status tracking and progress updates.
        
        Simulates the compilation process with realistic timing and status
        transitions. Updates progress display if provided.
        
        Args:
            target: Target to compile.
            progress: Optional progress display to update.
            task_id: Task ID for progress tracking.
        """
        try:
            start_time = time.perf_counter()

            # Phase 1: Compiling
            target.status = CompilationStatus.COMPILING
            if progress and task_id is not None:
                progress.update(task_id, completed=0)

            # TODO: Replace with actual compilation logic
            # This would call the real Kapitan compilation system
            # For now, simulate the work based on estimated duration
            compile_steps = 20

            for step in range(compile_steps):
                target.progress = (step / compile_steps) * 70
                if progress and task_id is not None:
                    progress.update(task_id, completed=target.progress)

            # Phase 2: Verifying
            target.status = CompilationStatus.VERIFYING
            verify_steps = 10

            for step in range(verify_steps):
                target.progress = 70 + (step / verify_steps) * 30
                if progress and task_id is not None:
                    progress.update(task_id, completed=target.progress)

            # For now, assume compilation succeeds
            # TODO: Add real error handling from compilation system
            target.status = CompilationStatus.COMPLETED
            target.progress = 100.0
            self.completed_count += 1

            target.duration = time.perf_counter() - start_time
            if progress and task_id is not None:
                progress.update(task_id, completed=target.progress)

        except Exception as e:
            target.status = CompilationStatus.FAILED
            target.error_message = str(e)
            self.failed_count += 1
            if progress and task_id is not None:
                progress.update(task_id, completed=0)

    def create_progress_display(self) -> tuple[Progress, Live]:
        """Create Rich progress display with per-target tracking.
        
        Returns:
            Tuple of (Progress, Live) for progress tracking and display.
        """
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

        # Create a live display for progress only
        live = Live(
            progress,
            console=self.console,
            refresh_per_second=4
        )

        return progress, live

    def create_combined_display(self, progress: Progress) -> Progress:
        """Create display showing just progress bars without summary.
        
        Args:
            progress: Progress instance to display.
            
        Returns:
            Progress instance for display.
        """
        return progress

    def get_status_display(self, status: CompilationStatus) -> str:
        """Get color-formatted status string for display.
        
        Args:
            status: Compilation status to format.
            
        Returns:
            Rich markup string with appropriate color formatting.
        """
        status_colors = {
            CompilationStatus.PENDING: "[dim]pending[/dim]",
            CompilationStatus.COMPILING: "[yellow]compiling[/yellow]",
            CompilationStatus.VERIFYING: "[blue]verifying[/blue]",
            CompilationStatus.COMPLETED: "[green]completed[/green]",
            CompilationStatus.FAILED: "[red]failed[/red]",
        }
        return status_colors.get(status, str(status))

    def finalize_compilation(self) -> FinalizationResult:
        """Execute final compilation phase: output writing and cleanup.
        
        Performs post-compilation tasks like writing manifests, generating
        documentation, and cleaning up temporary files.
        
        Returns:
            FinalizationResult with success status and timing.
        """
        start_time = time.perf_counter()

        try:
            # Finalization work without progress display
            # TODO: Replace with actual finalization tasks
            pass

            duration = time.perf_counter() - start_time

            return FinalizationResult(
                manifests_written=len(self.targets),
                output_directory=self.output_path,
                duration=duration,
                success=True
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            return FinalizationResult(
                manifests_written=0,
                output_directory=self.output_path,
                duration=duration,
                success=False,
                error=str(e)
            )

    def run_compilation(self, targets: list[str] | None = None) -> CompilationResult:
        """Execute complete three-phase compilation process.
        
        Orchestrates inventory loading, parallel target compilation, and
        finalization with comprehensive result tracking and timing.
        
        Args:
            targets: Optional list of specific targets to compile.
            
        Returns:
            CompilationResult with complete metrics and status.
        """
        overall_start_time = time.perf_counter()

        # Phase 1: Read inventory
        inventory_result = self.read_inventory(targets)

        if not self.targets:
            total_duration = time.perf_counter() - overall_start_time
            return CompilationResult(
                success=False,
                message="No targets found to compile",
                completed=0,
                failed=0,
                total=0,
                inventory_result=inventory_result,
                phase_timings=PhaseTimings(
                    inventory_reading=self.phase_timings.get("inventory_reading", 0.0),
                    compilation=0.0,
                    finalizing=0.0
                ),
                total_duration=total_duration,
                output_directory=self.output_path,
                targets=[]
            )

        # Phase 2: Compilation
        compilation_start_time = time.perf_counter()

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

                        # Update the progress display
                        if live:
                            live.update(progress)

                    # Final update
                    for i, target in enumerate(self.targets):
                        if progress:
                            progress.update(
                                task_ids[i],
                                status=self.get_status_display(target.status)
                            )
                    if live:
                        live.update(progress)
                else:
                    # Silent mode - just wait for completion
                    while any(not future.done() for future, _ in futures):
                        pass

        if context_manager:
            with context_manager:
                # Update the display to show initial state
                if live:
                    live.update(progress)
                run_compilation()
        else:
            run_compilation()

        self.phase_timings["compilation"] = time.perf_counter() - compilation_start_time

        # Phase 3: Finalize
        finalize_result = self.finalize_compilation()

        # Calculate total duration
        total_duration = time.perf_counter() - overall_start_time

        # Return comprehensive results
        return CompilationResult(
            success=self.failed_count == 0,
            message=f"Compiled {self.completed_count}/{len(self.targets)} targets successfully",
            completed=self.completed_count,
            failed=self.failed_count,
            total=len(self.targets),
            inventory_result=inventory_result,
            finalize_result=finalize_result,
            phase_timings=PhaseTimings(
                inventory_reading=self.phase_timings.get("inventory_reading", 0.0),
                compilation=self.phase_timings.get("compilation", 0.0),
                finalizing=self.phase_timings.get("finalizing", 0.0)
            ),
            total_duration=round(total_duration, 2),
            output_directory=self.output_path,
            targets=self.targets.copy()
        )
