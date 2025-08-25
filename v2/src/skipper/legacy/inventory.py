"""Legacy Kapitan inventory integration."""

import logging
import os
import sys
import time

from ..core.inventory import InventoryReader
from ..core.models import InventoryInfo, InventoryResult, TargetInfo
from .simple_reader import SimpleInventoryReader

logger = logging.getLogger(__name__)


class LegacyInventoryReader(InventoryReader):
    """Interface to read inventory data from legacy Kapitan."""

    def __init__(self, inventory_path: str = "inventory"):
        self.inventory_path = inventory_path
        self.simple_reader = SimpleInventoryReader(inventory_path)
        self.legacy_inventory = None
        self._targets_cache = None

    def _setup_legacy_path(self):
        """Add legacy Kapitan to Python path if needed."""
        legacy_path = "/home/coder/kapitan"
        if legacy_path not in sys.path:
            sys.path.insert(0, legacy_path)

    def _get_legacy_inventory(self):
        """Initialize legacy Kapitan inventory if not already done."""
        if self.legacy_inventory is not None:
            return self.legacy_inventory

        try:
            # Setup legacy path
            self._setup_legacy_path()

            # Import legacy inventory system directly
            from kapitan.inventory import get_inventory_backend

            # Force OmegaConf backend for variable interpolation
            try:
                inventory_class = get_inventory_backend("omegaconf")
                logger.info("Using OmegaConf inventory backend for variable interpolation")
                backend_name = "omegaconf"
            except Exception as e:
                logger.error(f"OmegaConf backend failed: {e}")
                raise e  # Don't fall back to reclass, force OmegaConf to work

            # Create inventory with minimal configuration to avoid multiprocessing issues
            self.legacy_inventory = inventory_class(
                inventory_path=self.inventory_path,
                compose_target_name=True
            )
            self.backend_name = backend_name

            # No need to restore paths since we're not manipulating them heavily

            return self.legacy_inventory

        except Exception as e:
            logger.error(f"Failed to initialize legacy inventory: {e}")
            # Log the error but don't need complex restoration
            return None

    def read_targets(self, target_filter: list[str] | None = None) -> InventoryResult:
        """Read targets from inventory with timing."""
        start_time = time.perf_counter()

        # First try the simple YAML reader
        try:
            result = self.simple_reader.read_targets(target_filter)
            if result.success and result.targets_found > 0:
                logger.info(f"Successfully loaded {result.targets_found} targets using simple YAML reader")
                return result
        except Exception as e:
            logger.debug(f"Simple reader failed: {e}")

        # Try the full legacy Kapitan system for OmegaConf support
        try:
            legacy_inv = self._get_legacy_inventory()
            if legacy_inv:
                logger.info("Trying legacy Kapitan inventory system with OmegaConf support")
                # Use the legacy inventory to render all targets
                # Handle 'all' filter by passing None (legacy Kapitan doesn't understand 'all')
                actual_filter = None if target_filter == ['all'] else target_filter
                logger.info(f"Requesting targets with filter: {actual_filter}")
                all_targets = legacy_inv.get_targets(actual_filter)
                logger.info(f"Legacy inventory returned {len(all_targets) if all_targets else 0} targets")

                targets = []
                for target_name, target_obj in all_targets.items():
                    logger.debug(f"Converting target: {target_name}")
                    target_info = self._convert_target(target_name, target_obj)
                    targets.append(target_info)

                duration = time.perf_counter() - start_time
                logger.info(f"Successfully loaded {len(targets)} targets using OmegaConf inventory")
                return InventoryResult(
                    success=True,
                    targets=targets,
                    targets_found=len(targets),
                    inventory_path=self.inventory_path,
                    duration=duration,
                    backend=f"legacy-{getattr(self, 'backend_name', 'unknown')}"
                )

        except Exception as e:
            logger.error(f"Legacy inventory system failed: {e}")

        # No fallback - require real inventory data
        logger.error("No valid inventory found and unable to read targets")
        return self._fallback_response(start_time, error="No inventory found or readable")

    def _convert_target(self, target_name: str, target_obj) -> TargetInfo:
        """Convert legacy target object to our format."""
        try:
            # Extract basic information
            classes = []
            applications = []
            parameters = {}
            target_type = "unknown"

            # Get classes if available
            if hasattr(target_obj, 'classes') and target_obj.classes:
                classes = [str(c) for c in target_obj.classes if c is not None]

            # Get applications/parameters if available
            if hasattr(target_obj, 'parameters'):
                if hasattr(target_obj.parameters, 'kapitan'):
                    kapitan_params = target_obj.parameters.kapitan

                    # Get compile parameters
                    if hasattr(kapitan_params, 'compile') and kapitan_params.compile:
                        compile_targets = kapitan_params.compile
                        for compile_target in compile_targets:
                            if hasattr(compile_target, 'input_type') and compile_target.input_type:
                                target_type = compile_target.input_type
                            if hasattr(compile_target, 'name') and compile_target.name:
                                applications.append(str(compile_target.name))

                # Store full parameters for reference
                if hasattr(target_obj.parameters, '__dict__'):
                    parameters = target_obj.parameters.__dict__

            return TargetInfo(
                name=target_name,
                classes=classes,
                applications=applications,
                type=target_type,
                parameters=parameters
            )

        except Exception as e:
            logger.debug(f"Error converting target {target_name}: {e}")
            return TargetInfo(
                name=target_name,
                classes=[],
                applications=[],
                type="unknown",
                parameters={},
                error=str(e)
            )

    def _fallback_response(self, start_time: float, error: str | None = None) -> InventoryResult:
        """Return fallback response when legacy inventory fails."""
        duration = time.time() - start_time
        return InventoryResult(
            success=False,
            targets=[],
            targets_found=0,
            inventory_path=self.inventory_path,
            duration=duration,
            backend="fallback",
            error=error
        )

    def check_inventory_exists(self) -> bool:
        """Check if inventory directory exists."""
        return self.simple_reader.check_inventory_exists()

    def get_inventory_info(self) -> InventoryInfo:
        """Get basic information about the inventory structure."""
        if not self.check_inventory_exists():
            return InventoryInfo(
                exists=False,
                targets_dir=None,
                classes_dir=None,
                target_files=[],
                class_files=[]
            )

        targets_dir = os.path.join(self.inventory_path, "targets")
        classes_dir = os.path.join(self.inventory_path, "classes")

        target_files = []
        class_files = []

        try:
            if os.path.exists(targets_dir):
                target_files = [f for f in os.listdir(targets_dir) if f.endswith('.yml') or f.endswith('.yaml')]

            if os.path.exists(classes_dir):
                class_files = [f for f in os.listdir(classes_dir) if f.endswith('.yml') or f.endswith('.yaml')]
        except Exception as e:
            logger.debug(f"Error reading inventory directories: {e}")

        return InventoryInfo(
            exists=True,
            targets_dir=targets_dir,
            classes_dir=classes_dir,
            target_files=sorted(target_files),
            class_files=sorted(class_files)
        )
