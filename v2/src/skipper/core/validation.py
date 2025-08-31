"""Data validation models and utilities using Pydantic.

Provides validated models for common data validation patterns including
path validation, directory checking, and inventory structure validation.
Ensures data integrity throughout the application.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValidatedPath(BaseModel):
    """Pydantic model for validating file system path existence.
    
    Ensures that provided paths exist on the file system and resolves
    them to absolute paths. Supports user home directory expansion.
    
    Attributes:
        path: Validated file system path as string.
    """

    model_config = ConfigDict(frozen=True)

    path: str = Field(..., description="File system path")

    @field_validator('path')
    @classmethod
    def validate_path_exists(cls, v: str) -> str:
        """Validate path existence and resolve to absolute path.
        
        Args:
            v: Path string to validate.
            
        Returns:
            Absolute path string.
            
        Raises:
            ValueError: If path is empty or doesn't exist.
        """
        if not v:
            raise ValueError("Path cannot be empty")

        path = Path(v).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Path does not exist: {v}")

        return str(path)

    def as_path(self) -> Path:
        """Return path as a Path object."""
        return Path(self.path)


class ValidatedDirectory(BaseModel):
    """Pydantic model for validating directory paths and accessibility.
    
    Ensures that provided paths exist, are directories, and can be read.
    Resolves paths to absolute form with user directory expansion.
    
    Attributes:
        path: Validated directory path as string.
    """

    model_config = ConfigDict(frozen=True)

    path: str = Field(..., description="Directory path")

    @field_validator('path')
    @classmethod
    def validate_directory(cls, v: str) -> str:
        """Validate that the path is a directory."""
        if not v:
            raise ValueError("Directory path cannot be empty")

        path = Path(v).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")

        return str(path)

    def as_path(self) -> Path:
        """Return path as a Path object."""
        return Path(self.path)

    def list_files(self, pattern: str = "*") -> list[Path]:
        """List files in the directory matching the pattern."""
        return list(Path(self.path).glob(pattern))


class ValidatedFile(BaseModel):
    """A Pydantic model for validating files."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(..., description="File path")

    @field_validator('path')
    @classmethod
    def validate_file(cls, v: str) -> str:
        """Validate that the path is a file."""
        if not v:
            raise ValueError("File path cannot be empty")

        path = Path(v).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"File does not exist: {v}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")

        return str(path)

    def as_path(self) -> Path:
        """Return path as a Path object."""
        return Path(self.path)

    def read_text(self, encoding: str = 'utf-8') -> str:
        """Read file content as text."""
        return Path(self.path).read_text(encoding=encoding)


class InventoryPathInfo(BaseModel):
    """Validated inventory path information."""

    model_config = ConfigDict(frozen=True)

    inventory_dir: ValidatedDirectory = Field(..., description="Main inventory directory")
    targets_dir: ValidatedDirectory | None = Field(None, description="Targets directory")
    classes_dir: ValidatedDirectory | None = Field(None, description="Classes directory")

    @field_validator('targets_dir', mode='before')
    @classmethod
    def validate_targets_dir(cls, v, info):
        """Validate targets directory exists within inventory."""
        if v is None:
            inventory_path = info.data.get('inventory_dir')
            if isinstance(inventory_path, ValidatedDirectory):
                targets_path = Path(inventory_path.path) / "targets"
                if targets_path.exists() and targets_path.is_dir():
                    return ValidatedDirectory(path=str(targets_path))
        return v

    @field_validator('classes_dir', mode='before')
    @classmethod
    def validate_classes_dir(cls, v, info):
        """Validate classes directory exists within inventory."""
        if v is None:
            inventory_path = info.data.get('inventory_dir')
            if isinstance(inventory_path, ValidatedDirectory):
                classes_path = Path(inventory_path.path) / "classes"
                if classes_path.exists() and classes_path.is_dir():
                    return ValidatedDirectory(path=str(classes_path))
        return v

    def get_target_files(self) -> list[Path]:
        """Get all target files in the inventory."""
        if not self.targets_dir:
            return []

        target_files = []
        for pattern in ["*.yml", "*.yaml"]:
            target_files.extend(self.targets_dir.list_files(pattern))

        return sorted(target_files)

    def get_class_files(self) -> list[Path]:
        """Get all class files in the inventory."""
        if not self.classes_dir:
            return []

        class_files = []
        for pattern in ["**/*.yml", "**/*.yaml"]:
            class_files.extend(self.classes_dir.list_files(pattern))

        return sorted(class_files)


class TargetPathInfo(BaseModel):
    """Validated target path information."""

    model_config = ConfigDict(frozen=True)

    file_path: ValidatedFile = Field(..., description="Target file path")
    inventory_dir: ValidatedDirectory = Field(..., description="Parent inventory directory")

    @field_validator('file_path')
    @classmethod
    def validate_target_file(cls, v: ValidatedFile) -> ValidatedFile:
        """Validate that the file is a YAML target file."""
        path = Path(v.path)
        if path.suffix not in ['.yml', '.yaml']:
            raise ValueError(f"Target file must be .yml or .yaml: {path}")

        return v

    def get_target_name(self) -> str:
        """Extract target name from file path."""
        targets_dir = self.inventory_dir.as_path() / "targets"
        file_path = Path(self.file_path.path)

        try:
            # Get relative path from targets directory
            rel_path = file_path.relative_to(targets_dir)
            # Remove the file extension to get target name
            target_name = str(rel_path.with_suffix(''))
            return target_name.replace('/', '.')  # Convert path separators to dots
        except ValueError as e:
            # File is not under targets directory
            raise ValueError(f"Target file must be under targets directory: {file_path}") from e

    def get_relative_path(self) -> str:
        """Get path relative to inventory directory."""
        try:
            file_path = Path(self.file_path.path)
            inventory_path = self.inventory_dir.as_path()
            return str(file_path.relative_to(inventory_path))
        except ValueError:
            return str(file_path)


# Convenience functions for common validation patterns
def validate_inventory_path(path: str) -> InventoryPathInfo:
    """
    Validate and create InventoryPathInfo from a path string.

    Args:
        path: Path to inventory directory

    Returns:
        InventoryPathInfo with validated paths

    Raises:
        ValidationError: If path is invalid
    """
    inventory_dir = ValidatedDirectory(path=path)
    return InventoryPathInfo(inventory_dir=inventory_dir)


def validate_target_file(file_path: str, inventory_path: str) -> TargetPathInfo:
    """
    Validate and create TargetPathInfo from file and inventory paths.

    Args:
        file_path: Path to target file
        inventory_path: Path to inventory directory

    Returns:
        TargetPathInfo with validated paths

    Raises:
        ValidationError: If paths are invalid
    """
    file_info = ValidatedFile(path=file_path)
    inventory_dir = ValidatedDirectory(path=inventory_path)
    return TargetPathInfo(file_path=file_info, inventory_dir=inventory_dir)


def validate_output_path(path: str, create_if_missing: bool = True) -> ValidatedDirectory:
    """
    Validate output directory path, optionally creating it if missing.

    Args:
        path: Path to output directory
        create_if_missing: Whether to create directory if it doesn't exist

    Returns:
        ValidatedDirectory for the output path

    Raises:
        ValidationError: If path is invalid or cannot be created
    """
    path_obj = Path(path).expanduser().resolve()

    if not path_obj.exists():
        if create_if_missing:
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Cannot create output directory {path}: {e}") from e
        else:
            raise ValueError(f"Output directory does not exist: {path}")

    return ValidatedDirectory(path=str(path_obj))
