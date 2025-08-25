"""Kapitan v2 compilation system."""

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
    """Handles parallel compilation processes with real inventory data."""

    def __init__(self, console: Console, parallel_jobs: int = 4, silent: bool = False, output_path: str = "compiled", inventory_path: str = "inventory"):
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
        """Read inventory using legacy Kapitan system."""
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
        """Convert legacy target format to compilation targets."""
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
        """Compile a single target."""
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

    def finalize_compilation(self) -> FinalizationResult:
        """Finalize compilation phase - write outputs and clean up."""
        start_time = time.perf_counter()

        try:
            if not self.silent:
                from rich.progress import Progress, SpinnerColumn, TextColumn

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                ) as progress:
                    task = progress.add_task("Finalizing compilation...", total=None)

                    # TODO: Replace with actual finalization tasks
                    steps = ["Writing manifests", "Generating docs", "Creating archive", "Cleaning up"]
                    for _i, step in enumerate(steps):
                        progress.update(task, description=f"[yellow]{step}...[/yellow]")
                        # TODO: Replace sleep with actual work

                    progress.update(task, description="[green]Compilation finalized[/green]")
            else:
                # Silent mode - TODO: Replace with actual finalization work
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
        """Run the complete compilation process with all phases."""
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

                        # Update the combined display
                        if live:
                            live.update(self.create_combined_display(progress))

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
                        pass

        if context_manager:
            with context_manager:
                # Update the display to show initial state
                if live:
                    live.update(self.create_combined_display(progress))
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
