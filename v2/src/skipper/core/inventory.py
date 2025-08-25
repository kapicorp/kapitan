"""Inventory reader interfaces and implementations."""

from abc import ABC, abstractmethod

from .models import InventoryInfo, InventoryResult


class InventoryReader(ABC):
    """Abstract base class for inventory readers."""

    def __init__(self, inventory_path: str):
        self.inventory_path = inventory_path

    @abstractmethod
    def read_targets(self, target_filter: list[str] | None = None) -> InventoryResult:
        """
        Read targets from inventory.

        Args:
            target_filter: Optional list of target patterns to filter

        Returns:
            InventoryResult containing targets and metadata
        """
        pass

    @abstractmethod
    def check_inventory_exists(self) -> bool:
        """Check if inventory directory exists and is valid."""
        pass

    @abstractmethod
    def get_inventory_info(self) -> InventoryInfo:
        """Get basic information about the inventory structure."""
        pass


class InventoryReaderFactory:
    """Factory for creating appropriate inventory readers."""

    _readers = {}

    @classmethod
    def register_reader(cls, name: str, reader_class: type) -> None:
        """Register a new inventory reader type."""
        cls._readers[name] = reader_class

    @classmethod
    def create_reader(cls, reader_type: str, inventory_path: str) -> InventoryReader:
        """
        Create an inventory reader of the specified type.

        Args:
            reader_type: Type of reader ('legacy', 'simple', etc.)
            inventory_path: Path to inventory directory

        Returns:
            InventoryReader instance

        Raises:
            ValueError: If reader_type is not registered
        """
        if reader_type not in cls._readers:
            available = ', '.join(cls._readers.keys())
            raise ValueError(f"Unknown reader type '{reader_type}'. Available: {available}")

        reader_class = cls._readers[reader_type]
        return reader_class(inventory_path)

    @classmethod
    def get_default_reader(cls, inventory_path: str) -> InventoryReader:
        """
        Get the default inventory reader for the given path.

        This method implements the logic for choosing the best reader
        based on the inventory structure and available features.
        """
        # Try to import and use the legacy reader by default
        # Fall back to simple reader if legacy is not available
        try:
            from ..legacy.inventory import LegacyInventoryReader
            return LegacyInventoryReader(inventory_path)
        except ImportError:
            from ..legacy.simple_reader import SimpleInventoryReader
            return SimpleInventoryReader(inventory_path)


# Register built-in readers
def _register_builtin_readers():
    """Register the built-in inventory readers."""
    try:
        from ..legacy.inventory import LegacyInventoryReader
        InventoryReaderFactory.register_reader('legacy', LegacyInventoryReader)
    except ImportError:
        pass

    try:
        from ..legacy.simple_reader import SimpleInventoryReader
        InventoryReaderFactory.register_reader('simple', SimpleInventoryReader)
    except ImportError:
        pass


# Register readers on module import
_register_builtin_readers()


# Convenience function for CLI commands
def get_inventory_reader(inventory_path: str, reader_type: str | None = None) -> InventoryReader:
    """
    Get an inventory reader instance.

    Args:
        inventory_path: Path to inventory directory
        reader_type: Optional specific reader type to use

    Returns:
        InventoryReader instance
    """
    if reader_type:
        return InventoryReaderFactory.create_reader(reader_type, inventory_path)
    else:
        return InventoryReaderFactory.get_default_reader(inventory_path)
