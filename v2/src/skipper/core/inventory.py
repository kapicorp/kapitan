"""Inventory reading system with pluggable backend support.

Provides abstract interfaces and factory pattern for inventory loading
from different sources. Supports legacy Kapitan inventory format and
simple YAML-based readers with automatic backend selection.
"""

from abc import ABC, abstractmethod

from .models import InventoryInfo, InventoryResult


class InventoryReader(ABC):
    """Abstract interface for inventory loading implementations.
    
    Defines the contract for reading target definitions from various
    inventory storage formats. Implementations handle specific formats
    like legacy Kapitan inventory or simplified YAML structures.
    
    Attributes:
        inventory_path: Path to inventory directory.
    """

    def __init__(self, inventory_path: str):
        """Initialize reader with inventory path.
        
        Args:
            inventory_path: Path to inventory directory to read from.
        """
        self.inventory_path = inventory_path

    @abstractmethod
    def read_targets(self, target_filter: list[str] | None = None) -> InventoryResult:
        """Read target definitions from inventory storage.
        
        Args:
            target_filter: Optional list of target patterns to filter results.
            
        Returns:
            InventoryResult with loaded targets and metadata.
        """
        pass

    @abstractmethod
    def check_inventory_exists(self) -> bool:
        """Verify that inventory directory exists and contains valid structure.
        
        Returns:
            True if inventory is accessible and valid, False otherwise.
        """
        pass

    @abstractmethod
    def get_inventory_info(self) -> InventoryInfo:
        """Retrieve metadata about inventory structure and contents.
        
        Returns:
            InventoryInfo with directory structure and file listings.
        """
        pass


class InventoryReaderFactory:
    """Factory for creating and managing inventory reader implementations.
    
    Provides registration system for different inventory reader types
    and automatic selection of appropriate readers based on inventory
    structure and availability.
    
    Attributes:
        _readers: Registry of available reader classes by name.
    """

    _readers = {}

    @classmethod
    def register_reader(cls, name: str, reader_class: type) -> None:
        """Register a new inventory reader implementation.
        
        Args:
            name: Unique identifier for the reader type.
            reader_class: InventoryReader implementation class.
        """
        cls._readers[name] = reader_class

    @classmethod
    def create_reader(cls, reader_type: str, inventory_path: str) -> InventoryReader:
        """Create inventory reader instance of specified type.
        
        Args:
            reader_type: Registered reader type name.
            inventory_path: Path to inventory directory.
            
        Returns:
            InventoryReader instance for the specified type.
            
        Raises:
            ValueError: If reader_type is not registered.
        """
        if reader_type not in cls._readers:
            available = ', '.join(cls._readers.keys())
            raise ValueError(f"Unknown reader type '{reader_type}'. Available: {available}")

        reader_class = cls._readers[reader_type]
        return reader_class(inventory_path)

    @classmethod
    def get_default_reader(cls, inventory_path: str) -> InventoryReader:
        """Get the best available inventory reader for the given path.
        
        Implements automatic reader selection based on availability
        and inventory structure, preferring legacy reader when available.
        
        Args:
            inventory_path: Path to inventory directory.
            
        Returns:
            InventoryReader instance best suited for the inventory.
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
    """Register all available built-in inventory reader implementations.
    
    Attempts to import and register legacy and simple readers,
    gracefully handling import failures for optional dependencies.
    """
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
    """Convenience function to get configured inventory reader.
    
    Args:
        inventory_path: Path to inventory directory.
        reader_type: Optional specific reader type, uses default if None.
        
    Returns:
        InventoryReader instance ready for use.
    """
    if reader_type:
        return InventoryReaderFactory.create_reader(reader_type, inventory_path)
    else:
        return InventoryReaderFactory.get_default_reader(inventory_path)
