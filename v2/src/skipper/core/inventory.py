"""Inventory reading system with pluggable backend support.

Provides abstract interfaces and factory pattern for inventory loading
from different sources. Supports legacy Kapitan inventory format and
simple YAML-based readers with automatic backend selection.
"""

import logging
from abc import ABC, abstractmethod

from .models import InventoryInfo, InventoryResult

logger = logging.getLogger(__name__)


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
        
        Implements intelligent reader selection based on availability,
        inventory structure, and feature requirements. The enhanced
        legacy reader provides sophisticated fallback strategies.
        
        Args:
            inventory_path: Path to inventory directory.
            
        Returns:
            InventoryReader instance optimized for the inventory structure.
        """
        # Always prefer the enhanced legacy reader which includes
        # intelligent fallback to simple reader when appropriate
        try:
            from ..legacy.inventory import LegacyInventoryReader
            reader = LegacyInventoryReader(inventory_path)
            # The enhanced legacy reader automatically handles fallback
            # to simple reader when legacy Kapitan is not available
            return reader
        except ImportError:
            # Fallback to simple reader if legacy module is not available
            from ..legacy.simple_reader import SimpleInventoryReader
            return SimpleInventoryReader(inventory_path)


# Register built-in readers
def _register_builtin_readers():
    """Register all available built-in inventory reader implementations.
    
    Enhanced registration that properly handles the improved legacy reader
    with its intelligent fallback capabilities and backend selection.
    """
    try:
        from ..legacy.inventory import LegacyInventoryReader
        InventoryReaderFactory.register_reader('legacy', LegacyInventoryReader)
        InventoryReaderFactory.register_reader('enhanced', LegacyInventoryReader)  # Alias for enhanced capabilities
        logger.debug("Registered enhanced legacy inventory reader with intelligent fallback")
    except ImportError:
        logger.debug("Enhanced legacy inventory reader not available")

    try:
        from ..legacy.simple_reader import SimpleInventoryReader
        InventoryReaderFactory.register_reader('simple', SimpleInventoryReader)
        logger.debug("Registered simple YAML inventory reader")
    except ImportError:
        logger.debug("Simple inventory reader not available")


# Convenience function for CLI commands
def get_inventory_reader(inventory_path: str, reader_type: str | None = None) -> InventoryReader:
    """Convenience function to get configured inventory reader.
    
    Args:
        inventory_path: Path to inventory directory.
        reader_type: Optional specific reader type, uses default if None.
        
    Returns:
        InventoryReader instance ready for use.
    """
    # Ensure readers are registered
    _ensure_readers_registered()
    
    if reader_type:
        return InventoryReaderFactory.create_reader(reader_type, inventory_path)
    else:
        return InventoryReaderFactory.get_default_reader(inventory_path)


# Lazy registration to avoid circular imports
_readers_registered = False

def _ensure_readers_registered():
    """Ensure readers are registered exactly once."""
    global _readers_registered
    if not _readers_registered:
        _register_builtin_readers()
        _readers_registered = True
