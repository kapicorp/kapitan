"""Pydantic models for Kapitan v2 core data structures."""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class CompilationStatus(str, Enum):
    """Compilation status for individual targets."""
    PENDING = "pending"
    COMPILING = "compiling"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class TargetInfo(BaseModel):
    """Information about a target from inventory."""
    name: str
    classes: list[str] = Field(default_factory=list)
    applications: list[str] = Field(default_factory=list)
    type: str = "unknown"
    parameters: dict = Field(default_factory=dict)
    error: str | None = None


class CompilationTarget(BaseModel):
    """Represents a compilation target with status tracking."""
    name: str
    status: CompilationStatus = CompilationStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    duration: float = Field(default=0.0, ge=0.0)
    error_message: str | None = None
    output_path: str | None = None

    @computed_field
    @property
    def is_completed(self) -> bool:
        """Check if target compilation is completed (success or failure)."""
        return self.status in [CompilationStatus.COMPLETED, CompilationStatus.FAILED]

    @computed_field
    @property
    def is_successful(self) -> bool:
        """Check if target compilation was successful."""
        return self.status == CompilationStatus.COMPLETED


class InventoryResult(BaseModel):
    """Result of inventory reading operation."""
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
        """Get list of target names."""
        return [target.name for target in self.targets]


class PhaseTimings(BaseModel):
    """Timing information for compilation phases."""
    inventory_reading: float = Field(ge=0.0)
    compilation: float = Field(ge=0.0)
    finalizing: float = Field(ge=0.0)

    @computed_field
    @property
    def total_duration(self) -> float:
        """Calculate total duration across all phases."""
        return self.inventory_reading + self.compilation + self.finalizing


class FinalizationResult(BaseModel):
    """Result of compilation finalization phase."""
    manifests_written: int = Field(ge=0)
    output_directory: str | Path
    duration: float = Field(ge=0.0)
    success: bool = True
    error: str | None = None


class CompilationResult(BaseModel):
    """Comprehensive result of compilation operation."""
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
        """Calculate completion rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100.0

    @computed_field
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.failed / self.total) * 100.0

    @computed_field
    @property
    def in_progress_count(self) -> int:
        """Calculate number of targets still in progress."""
        return self.total - self.completed - self.failed


class InventoryInfo(BaseModel):
    """Information about inventory structure."""
    exists: bool
    targets_dir: str | Path | None = None
    classes_dir: str | Path | None = None
    target_files: list[str] = Field(default_factory=list)
    class_files: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def has_targets(self) -> bool:
        """Check if inventory has target files."""
        return len(self.target_files) > 0

    @computed_field
    @property
    def has_classes(self) -> bool:
        """Check if inventory has class files."""
        return len(self.class_files) > 0


class CLIResult(BaseModel):
    """Standardized result structure for CLI operations."""
    success: bool
    data: CompilationResult | InventoryResult | dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    error: str | None = None

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v)
        }
