"""Core data models for Skipper using Pydantic.

Defines the primary data structures used throughout the application:
- Configuration and compilation results
- Target and inventory information  
- Status tracking and timing models
- CLI operation results
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class CompilationStatus(str, Enum):
    """Status values for tracking target compilation progress.
    
    Attributes:
        PENDING: Target queued for compilation.
        COMPILING: Target currently being compiled.
        VERIFYING: Target output being verified.
        COMPLETED: Target successfully compiled.
        FAILED: Target compilation failed.
    """
    PENDING = "pending"
    COMPILING = "compiling"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class TargetInfo(BaseModel):
    """Metadata for a target loaded from inventory.
    
    Attributes:
        name: Target identifier.
        classes: List of class names this target inherits.
        applications: List of applications this target defines.
        type: Target type (e.g., 'jsonnet', 'jinja2').
        parameters: Target-specific configuration parameters.
        error: Error message if target loading failed.
    """
    name: str
    classes: list[str] = Field(default_factory=list)
    applications: list[str] = Field(default_factory=list)
    type: str = "unknown"
    parameters: dict = Field(default_factory=dict)
    error: str | None = None


class CompilationTarget(BaseModel):
    """Compilation target with real-time status and progress tracking.
    
    Attributes:
        name: Target name being compiled.
        status: Current compilation status.
        progress: Completion percentage (0-100).
        duration: Time taken for compilation in seconds.
        error_message: Error details if compilation failed.
        output_path: Path where compiled output is written.
    """
    name: str
    status: CompilationStatus = CompilationStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    duration: float = Field(default=0.0, ge=0.0)
    error_message: str | None = None
    output_path: str | None = None

    @computed_field
    @property
    def is_completed(self) -> bool:
        """Check if target has finished compilation (successfully or with failure).
        
        Returns:
            True if compilation is complete, False if still in progress.
        """
        return self.status in [CompilationStatus.COMPLETED, CompilationStatus.FAILED]

    @computed_field
    @property
    def is_successful(self) -> bool:
        """Check if target compilation completed successfully.
        
        Returns:
            True if compilation succeeded, False otherwise.
        """
        return self.status == CompilationStatus.COMPLETED


class InventoryResult(BaseModel):
    """Result of loading and parsing inventory from storage.
    
    Attributes:
        success: Whether inventory loading succeeded.
        targets: List of targets found in inventory.
        targets_found: Total number of targets discovered.
        inventory_path: Path where inventory was loaded from.
        duration: Time taken to load inventory in seconds.
        backend: Backend used for loading (e.g., 'simple-yaml').
        error: Error message if loading failed.
    """
    success: bool
    targets: list[TargetInfo] = Field(default_factory=list)
    targets_found: int = 0
    inventory_path: str
    duration: float = Field(ge=0.0)
    backend: str
    error: str | None = None

    @computed_field
    @property
    def target_names(self) -> list[str]:
        """Extract target names from loaded target information.
        
        Returns:
            List of target name strings.
        """
        return [target.name for target in self.targets]


class PhaseTimings(BaseModel):
    """Detailed timing metrics for each compilation phase.
    
    Attributes:
        inventory_reading: Time spent loading inventory in seconds.
        compilation: Time spent compiling targets in seconds.
        finalizing: Time spent in finalization phase in seconds.
    """
    inventory_reading: float = Field(ge=0.0)
    compilation: float = Field(ge=0.0)
    finalizing: float = Field(ge=0.0)

    @computed_field
    @property
    def total_duration(self) -> float:
        """Calculate total compilation time across all phases.
        
        Returns:
            Sum of all phase durations in seconds.
        """
        return self.inventory_reading + self.compilation + self.finalizing


class FinalizationResult(BaseModel):
    """Result of the final compilation phase that writes output.
    
    Attributes:
        manifests_written: Number of manifest files written to output.
        output_directory: Directory where compilation output was written.
        duration: Time taken for finalization in seconds.
        success: Whether finalization completed successfully.
        error: Error message if finalization failed.
    """
    manifests_written: int = Field(ge=0)
    output_directory: str | Path
    duration: float = Field(ge=0.0)
    success: bool = True
    error: str | None = None


class CompilationResult(BaseModel):
    """Complete compilation result with metrics, timing, and target status.
    
    Attributes:
        success: Overall compilation success status.
        message: Human-readable summary message.
        completed: Number of targets that compiled successfully.
        failed: Number of targets that failed compilation.
        total: Total number of targets processed.
        inventory_result: Result of inventory loading phase.
        finalize_result: Result of finalization phase.
        phase_timings: Detailed timing for each compilation phase.
        total_duration: Total time for entire compilation.
        output_directory: Directory where output was written.
        targets: List of individual target compilation results.
        timestamp: When compilation was performed.
    """
    success: bool
    message: str
    completed: int = Field(ge=0)
    failed: int = Field(ge=0)
    total: int = Field(ge=0)
    inventory_result: InventoryResult
    finalize_result: FinalizationResult | None = None
    phase_timings: PhaseTimings
    total_duration: float = Field(ge=0.0)
    output_directory: str | Path
    targets: list[CompilationTarget] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def completion_rate(self) -> float:
        """Calculate percentage of targets that completed successfully.
        
        Returns:
            Completion rate as percentage (0-100).
        """
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100.0

    @computed_field
    @property
    def failure_rate(self) -> float:
        """Calculate percentage of targets that failed compilation.
        
        Returns:
            Failure rate as percentage (0-100).
        """
        if self.total == 0:
            return 0.0
        return (self.failed / self.total) * 100.0

    @computed_field
    @property
    def in_progress_count(self) -> int:
        """Calculate number of targets currently being processed.
        
        Returns:
            Count of targets not yet completed or failed.
        """
        return self.total - self.completed - self.failed


class InventoryInfo(BaseModel):
    """Metadata about inventory directory structure and contents.
    
    Attributes:
        exists: Whether the inventory directory exists.
        targets_dir: Path to targets directory.
        classes_dir: Path to classes directory.
        target_files: List of target definition files found.
        class_files: List of class definition files found.
    """
    exists: bool
    targets_dir: str | Path | None = None
    classes_dir: str | Path | None = None
    target_files: list[str] = Field(default_factory=list)
    class_files: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def has_targets(self) -> bool:
        """Check if any target definition files were found.
        
        Returns:
            True if target files exist, False otherwise.
        """
        return len(self.target_files) > 0

    @computed_field
    @property
    def has_classes(self) -> bool:
        """Check if any class definition files were found.
        
        Returns:
            True if class files exist, False otherwise.
        """
        return len(self.class_files) > 0


class CLIResult(BaseModel):
    """Standardized result container for all CLI command operations.
    
    Provides a consistent structure for command results that can be
    formatted as console output, plain text, or JSON.
    
    Attributes:
        success: Whether the operation completed successfully.
        data: Command-specific result data.
        timestamp: When the operation was performed.
        error: Error message if operation failed.
    """
    success: bool
    data: CompilationResult | InventoryResult | dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    error: str | None = None

    class Config:
        """Pydantic model configuration for JSON serialization."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v)
        }
