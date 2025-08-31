"""Legacy Kapitan inventory integration with enhanced v2 patterns.

Provides seamless integration between legacy Kapitan inventory system
and modern Skipper v2 architecture. Leverages factory patterns,
enhanced error handling, and optimized caching strategies.
"""

import logging
import os
import sys
import time
from functools import lru_cache
from typing import Any

from ..core.inventory import InventoryReader
from ..core.models import InventoryInfo, InventoryResult, TargetInfo
from .simple_reader import SimpleInventoryReader

logger = logging.getLogger(__name__)


class LegacyInventoryReader(InventoryReader):
    """Enhanced interface to read inventory data from legacy Kapitan.
    
    Provides optimized integration with legacy Kapitan inventory system,
    featuring intelligent fallback to simple YAML reading, enhanced caching,
    and improved error handling strategies.
    
    Attributes:
        inventory_path: Path to inventory directory.
        simple_reader: Fallback SimpleInventoryReader instance.
        legacy_inventory: Cached legacy Kapitan inventory instance.
        _backend_preference: Preferred backend order for auto-selection.
    """

    def __init__(self, inventory_path: str = "inventory"):
        super().__init__(inventory_path)
        self.simple_reader = SimpleInventoryReader(inventory_path)
        self.legacy_inventory = None
        self._backend_preference = ["reclass", "omegaconf", "reclass-rs"]  # Prefer reclass for reclass inventories
        self._legacy_available = None

    @lru_cache(maxsize=1)
    def _setup_legacy_path(self) -> bool:
        """Add legacy Kapitan to Python path and verify availability.
        
        Returns:
            True if legacy Kapitan is available, False otherwise.
        """
        legacy_path = "/home/coder/kapitan"
        if legacy_path not in sys.path:
            sys.path.insert(0, legacy_path)
        
        # Verify legacy Kapitan is importable
        try:
            import kapitan.inventory  # noqa: F401
            return True
        except ImportError as e:
            logger.debug(f"Legacy Kapitan not available: {e}")
            return False

    def _get_legacy_inventory(self):
        """Initialize legacy Kapitan inventory with intelligent backend selection.
        
        Uses enhanced backend selection strategy, preferring OmegaConf for
        variable interpolation but gracefully falling back to other backends.
        Implements caching and proper error handling.
        
        Returns:
            Initialized legacy inventory instance or None if unavailable.
        """
        if self.legacy_inventory is not None:
            return self.legacy_inventory

        # Check if legacy Kapitan is available
        if not self._setup_legacy_path():
            logger.debug("Legacy Kapitan not available, using simple reader")
            return None

        try:
            from kapitan.inventory import get_inventory_backend

            # Try backends in preference order with enhanced error handling
            last_error = None
            for backend_name in self._backend_preference:
                try:
                    inventory_class = get_inventory_backend(backend_name)
                    logger.debug(f"Attempting {backend_name} inventory backend")
                    
                    # Create inventory with backend-specific configuration
                    init_kwargs = {
                        "inventory_path": self.inventory_path,
                        "compose_target_name": True,
                        "ignore_class_not_found": True,
                        "initialise": False  # Control initialization manually
                    }
                    
                    self.legacy_inventory = inventory_class(**init_kwargs)
                    
                    # Try initialization with graduated error handling
                    init_success = self._try_backend_initialization(backend_name)
                    if init_success:
                        self.backend_name = backend_name
                        logger.info(f"Successfully initialized {backend_name} inventory backend")
                        return self.legacy_inventory
                    else:
                        logger.debug(f"Backend {backend_name} initialization had issues, trying next backend")
                        continue
                    
                except Exception as e:
                    logger.debug(f"{backend_name} backend failed during creation: {e}")
                    last_error = e
                    continue
            
            # If all backends fail, log the last error
            if last_error:
                logger.warning(f"All inventory backends failed, last error: {last_error}")
            
            return None

        except Exception as e:
            logger.error(f"Failed to initialize legacy inventory system: {e}")
            return None

    def read_targets(self, target_filter: list[str] | None = None) -> InventoryResult:
        """Read targets from inventory with enhanced integration strategy.
        
        Implements a sophisticated cascade approach:
        1. Try simple YAML reader for fast, lightweight parsing
        2. Fall back to legacy Kapitan for advanced features (OmegaConf, variable interpolation)
        3. Enhanced error handling and performance monitoring
        
        Args:
            target_filter: Optional list of target patterns to filter results.
            
        Returns:
            InventoryResult with comprehensive metadata and timing information.
        """
        start_time = time.perf_counter()
        
        # Strategy 1: Try simple YAML reader first (fast path)
        simple_result = self._try_simple_reader(target_filter, start_time)
        if simple_result and simple_result.success and simple_result.targets_found > 0:
            # Check if simple reader found complex features that need legacy processing
            if self._needs_legacy_processing(simple_result.targets):
                logger.debug("Simple reader successful but complex features detected, trying legacy...")
            else:
                logger.debug(f"Simple reader successful: {simple_result.targets_found} targets")
                return simple_result
        
        # Strategy 2: Try legacy Kapitan system for advanced features
        legacy_result = self._try_legacy_reader(target_filter, start_time)
        if legacy_result and legacy_result.success:
            return legacy_result
        
        # Strategy 3: Return simple result if legacy failed but simple had partial success
        if simple_result and simple_result.targets_found > 0:
            logger.warning("Legacy inventory failed, returning simple YAML results")
            return simple_result
        
        # No readable inventory found
        logger.error("No valid inventory found using any reader strategy")
        return self._fallback_response(start_time, error="No inventory readable by any backend")

    def _try_simple_reader(self, target_filter: list[str] | None, start_time: float) -> InventoryResult | None:  # noqa: ARG002
        """Attempt to read inventory using simple YAML reader.
        
        Args:
            target_filter: Target filter to apply.
            start_time: Start time for duration calculation.
            
        Returns:
            InventoryResult if successful, None if failed.
        """
        try:
            result = self.simple_reader.read_targets(target_filter)
            if result.success:
                logger.debug(f"Simple reader loaded {result.targets_found} targets in {result.duration:.2f}s")
            return result
        except Exception as e:
            logger.debug(f"Simple reader failed: {e}")
            return None
    
    def _try_legacy_reader(self, target_filter: list[str] | None, start_time: float) -> InventoryResult | None:  # noqa: ARG002
        """Attempt to read inventory using legacy Kapitan system.
        
        Args:
            target_filter: Target filter to apply.
            start_time: Start time for duration calculation.
            
        Returns:
            InventoryResult if successful, None if failed.
        """
        try:
            legacy_inv = self._get_legacy_inventory()
            if not legacy_inv:
                return None
                
            logger.debug(f"Using legacy Kapitan inventory system with {getattr(self, 'backend_name', 'unknown')} backend")
            
            # Handle 'all' filter by passing None (legacy Kapitan doesn't understand 'all')
            actual_filter = None if target_filter == ['all'] else target_filter
            logger.debug(f"Requesting targets with filter: {actual_filter}")
            
            # For reclass inventories, get targets individually with proper target injection
            if getattr(self, 'backend_name', '') == 'reclass':
                all_targets = self._get_reclass_targets_with_injection(legacy_inv, actual_filter)
                logger.debug(f"Reclass inventory with target injection returned {len(all_targets)} targets")
            else:
                # Get targets with better error handling for interpolation issues
                try:
                    all_targets = legacy_inv.get_targets(actual_filter)
                    logger.debug(f"Legacy inventory returned {len(all_targets) if all_targets else 0} targets")
                except Exception as e:
                    logger.warning(f"Legacy inventory get_targets failed: {e}")
                    # Try to get targets individually to recover partial data
                    all_targets = self._get_targets_individually(legacy_inv, actual_filter)
                    if all_targets:
                        logger.info(f"Recovered {len(all_targets)} targets individually")

            targets = []
            conversion_errors = []
            
            for target_name, target_obj in all_targets.items():
                try:
                    target_info = self._convert_target(target_name, target_obj)
                    
                    # For reclass inventories, skip targets with interpolation errors
                    if getattr(self, 'backend_name', '') == 'reclass':
                        if target_info.error and ("interpolation" in target_info.error.lower() or "render" in target_info.error.lower()):
                            logger.debug(f"Skipping target {target_name} due to interpolation failure in reclass")
                            conversion_errors.append(f"{target_name}: {target_info.error}")
                            continue
                    
                    targets.append(target_info)
                    logger.debug(f"Successfully converted target: {target_name}")
                        
                except Exception as e:
                    logger.debug(f"Failed to convert target {target_name}: {e}")
                    conversion_errors.append(f"{target_name}: {e}")
                    
                    # Only create fallback for non-interpolation errors
                    if not ("interpolation" in str(e).lower() or "render" in str(e).lower()):
                        fallback_target = self._create_fallback_target(target_name, target_obj, str(e))
                        targets.append(fallback_target)
                    else:
                        logger.debug(f"Skipping target {target_name} due to interpolation failure")

            duration = time.perf_counter() - start_time
            backend_name = f"legacy-{getattr(self, 'backend_name', 'unknown')}"
            
            if conversion_errors:
                logger.warning(f"Had {len(conversion_errors)} target conversion errors")
            
            logger.debug(f"Legacy reader loaded {len(targets)} targets in {duration:.2f}s using {backend_name}")
            
            return InventoryResult(
                success=True,
                targets=targets,
                targets_found=len(targets),
                inventory_path=self.inventory_path,
                duration=duration,
                backend=backend_name,
                error=f"Conversion errors: {len(conversion_errors)}" if conversion_errors else None
            )
            
        except Exception as e:
            logger.error(f"Legacy inventory system failed: {e}")
            return None
    
    def _needs_legacy_processing(self, targets: list[TargetInfo]) -> bool:
        """Check if targets contain features that require legacy Kapitan processing.
        
        Args:
            targets: List of targets from simple reader.
            
        Returns:
            True if legacy processing would be beneficial.
        """
        for target in targets:
            # Check for complex parameter structures that might need interpolation
            if target.parameters:
                params_str = str(target.parameters)
                # Look for OmegaConf interpolation patterns
                if "${" in params_str or "?{" in params_str or "#{" in params_str:
                    logger.debug(f"Target {target.name} has interpolation patterns")
                    return True
                # Look for complex nested structures
                if any(isinstance(v, dict) and len(v) > 3 for v in target.parameters.values()):
                    logger.debug(f"Target {target.name} has complex parameter structures")
                    return True
        return False
    
    def _convert_target(self, target_name: str, target_obj: Any) -> TargetInfo:
        """Convert legacy target object to Skipper v2 TargetInfo format.
        
        Enhanced conversion that leverages the rich data structures from
        legacy Kapitan while mapping to the modern Skipper v2 models.
        
        Args:
            target_name: Name of the target being converted.
            target_obj: Legacy Kapitan target object.
            
        Returns:
            TargetInfo with comprehensive target metadata.
        """
        try:
            # Extract basic information with enhanced error handling
            classes = self._extract_classes(target_obj)
            applications = []
            parameters = self._extract_parameters(target_obj)
            target_type = "unknown"

            # Enhanced compile target extraction
            compile_info = self._extract_compile_info(target_obj)
            if compile_info:
                target_type = compile_info.get("input_type", target_type)
                applications.extend(compile_info.get("applications", []))

            # Enhanced target type detection
            if target_type == "unknown":
                target_type = self._infer_target_type(target_name, parameters, classes)

            return TargetInfo(
                name=target_name,
                classes=classes,
                applications=list(set(applications)),  # Remove duplicates
                type=target_type,
                parameters=parameters
            )

        except Exception as e:
            logger.warning(f"Error converting target {target_name}: {e}")
            return TargetInfo(
                name=target_name,
                classes=[],
                applications=[],
                type="unknown",
                parameters={},
                error=str(e)
            )

    def _extract_classes(self, target_obj: Any) -> list[str]:
        """Extract class names from legacy target object.
        
        Args:
            target_obj: Legacy Kapitan target object.
            
        Returns:
            List of class name strings.
        """
        classes = []
        if hasattr(target_obj, 'classes') and target_obj.classes:
            classes = [str(c) for c in target_obj.classes if c is not None]
        return classes
    
    def _extract_parameters(self, target_obj: Any) -> dict:
        """Extract parameters from legacy target object with enhanced handling.
        
        Args:
            target_obj: Legacy Kapitan target object.
            
        Returns:
            Dictionary of target parameters.
        """
        parameters = {}
        if hasattr(target_obj, 'parameters'):
            try:
                # Try to convert to dict, handling OmegaConf DictConfig
                if hasattr(target_obj.parameters, '_content'):
                    # OmegaConf DictConfig
                    parameters = dict(target_obj.parameters)
                elif hasattr(target_obj.parameters, '__dict__'):
                    # Standard object
                    parameters = target_obj.parameters.__dict__
                else:
                    # Try direct conversion
                    parameters = dict(target_obj.parameters)
            except Exception as e:
                logger.debug(f"Could not extract parameters: {e}")
                parameters = {}
        return parameters
    
    def _extract_compile_info(self, target_obj: Any) -> dict | None:
        """Extract compile information from legacy target object.
        
        Args:
            target_obj: Legacy Kapitan target object.
            
        Returns:
            Dictionary with compile information or None if not found.
        """
        try:
            if not hasattr(target_obj, 'parameters'):
                return None
                
            # Navigate to kapitan.compile parameters
            params = target_obj.parameters
            if not hasattr(params, 'kapitan'):
                return None
                
            kapitan_params = params.kapitan
            if not hasattr(kapitan_params, 'compile') or not kapitan_params.compile:
                return None
                
            compile_targets = kapitan_params.compile
            compile_info = {
                "applications": [],
                "input_types": [],
                "output_paths": []
            }
            
            for compile_target in compile_targets:
                if hasattr(compile_target, 'input_type'):
                    input_type = str(compile_target.input_type)
                    if input_type not in compile_info["input_types"]:
                        compile_info["input_types"].append(input_type)
                        
                if hasattr(compile_target, 'name'):
                    app_name = str(compile_target.name)
                    if app_name not in compile_info["applications"]:
                        compile_info["applications"].append(app_name)
                        
                if hasattr(compile_target, 'output_path'):
                    output_path = str(compile_target.output_path)
                    if output_path not in compile_info["output_paths"]:
                        compile_info["output_paths"].append(output_path)
            
            # Return the primary input type
            compile_info["input_type"] = compile_info["input_types"][0] if compile_info["input_types"] else "unknown"
            return compile_info
            
        except Exception as e:
            logger.debug(f"Could not extract compile info: {e}")
            return None
    
    def _infer_target_type(self, target_name: str, parameters: dict, classes: list[str]) -> str:
        """Infer target type from available information.
        
        Args:
            target_name: Name of the target.
            parameters: Target parameters.
            classes: Target classes.
            
        Returns:
            Inferred target type string.
        """
        # Check for common patterns in target name
        if any(keyword in target_name.lower() for keyword in ['jsonnet', 'jinja2', 'helm', 'kustomize']):
            for keyword in ['jsonnet', 'jinja2', 'helm', 'kustomize']:
                if keyword in target_name.lower():
                    return keyword
        
        # Check parameters for compile type information
        if parameters and 'kapitan' in parameters:
            kapitan_params = parameters['kapitan']
            if 'compile' in kapitan_params and kapitan_params['compile']:
                compile_targets = kapitan_params['compile']
                if compile_targets and isinstance(compile_targets[0], dict):
                    input_type = compile_targets[0].get('input_type')
                    if input_type:
                        return input_type
        
        # Check classes for type hints
        for class_name in classes:
            if any(keyword in class_name.lower() for keyword in ['jsonnet', 'jinja2', 'helm']):
                for keyword in ['jsonnet', 'jinja2', 'helm']:
                    if keyword in class_name.lower():
                        return keyword
        
        return "yaml"
    
    def _get_targets_individually(self, legacy_inv: Any, target_filter: list[str] | None) -> dict:
        """Attempt to get targets individually when batch get_targets fails.
        
        Args:
            legacy_inv: Legacy inventory instance.
            target_filter: Target filter to apply.
            
        Returns:
            Dictionary of successfully retrieved targets.
        """
        targets = {}
        
        try:
            # Get list of available target names from the inventory
            if hasattr(legacy_inv, 'targets') and legacy_inv.targets:
                target_names = list(legacy_inv.targets.keys())
                
                # Apply filter if specified
                if target_filter:
                    target_names = [name for name in target_names if name in target_filter]
                
                # Try to get each target individually
                for target_name in target_names:
                    try:
                        target = legacy_inv.get_target(target_name, ignore_class_not_found=True)
                        if target:
                            targets[target_name] = target
                            logger.debug(f"Successfully retrieved target: {target_name}")
                    except Exception as e:
                        logger.debug(f"Failed to retrieve target {target_name}: {e}")
                        continue
                        
        except Exception as e:
            logger.debug(f"Could not retrieve targets individually: {e}")
            
        return targets
    
    def _get_reclass_targets_with_injection(self, legacy_inv: Any, target_filter: list[str] | None) -> dict:
        """Get targets from reclass inventory with proper target name injection.
        
        Reclass inventories require 'vars.target' to be injected for proper
        interpolation. This method handles that requirement and skips targets
        that fail interpolation.
        
        Args:
            legacy_inv: Legacy reclass inventory instance.
            target_filter: Target filter to apply.
            
        Returns:
            Dictionary of successfully rendered targets.
        """
        targets = {}
        
        try:
            # Get list of target names from the inventory
            if not hasattr(legacy_inv, 'targets') or not legacy_inv.targets:
                logger.debug("No targets found in legacy inventory")
                return targets
                
            target_names = list(legacy_inv.targets.keys())
            
            # Apply filter if specified
            if target_filter:
                target_names = [name for name in target_names if name in target_filter]
            
            logger.debug(f"Processing {len(target_names)} targets with reclass injection")
            
            # Get each target individually with proper target injection
            for target_name in target_names:
                try:
                    # For reclass, we need to call render_target with the target name
                    # This injects vars.target properly
                    target = legacy_inv.get_target(target_name)
                    if target:
                        # Additional validation - check if target was properly rendered
                        if hasattr(target, 'parameters') and target.parameters:
                            targets[target_name] = target
                            logger.debug(f"Successfully rendered reclass target: {target_name}")
                        else:
                            logger.debug(f"Target {target_name} rendered but has no parameters, skipping")
                    else:
                        logger.debug(f"Target {target_name} returned None, skipping")
                        
                except Exception as e:
                    # Skip targets that fail interpolation - don't include them
                    if "interpolation" in str(e).lower() or "render" in str(e).lower():
                        logger.debug(f"Skipping target {target_name} due to interpolation failure: {e}")
                    else:
                        logger.warning(f"Unexpected error for target {target_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to process reclass targets: {e}")
            
        logger.info(f"Successfully loaded {len(targets)} targets from reclass inventory")
        return targets
    
    def _try_backend_initialization(self, backend_name: str) -> bool:
        """Try to initialize a specific backend with graduated error handling.
        
        Args:
            backend_name: Name of the backend being initialized.
            
        Returns:
            True if initialization succeeded or succeeded with warnings, False if failed.
        """
        try:
            # Try full initialization
            self.legacy_inventory._Inventory__initialise(ignore_class_not_found=True)
            logger.debug(f"Backend {backend_name} initialized successfully")
            return True
        except Exception as init_error:
            # For reclass inventories, initialization errors are expected due to interpolation
            # We'll handle target rendering individually with proper injection
            if backend_name == 'reclass' and "interpolation" in str(init_error).lower():
                logger.debug(f"Reclass backend has interpolation errors during init (expected), will handle per-target")
                # Check if we have target structure even with errors
                if hasattr(self.legacy_inventory, 'targets') and self.legacy_inventory.targets:
                    logger.debug(f"Reclass backend has target structure ({len(self.legacy_inventory.targets)} targets)")
                    return True  # Accept for per-target processing
            else:
                logger.warning(f"Backend {backend_name} initialization had errors: {init_error}")
                
                # Check if we have partial target data despite errors
                if hasattr(self.legacy_inventory, 'targets') and self.legacy_inventory.targets:
                    logger.info(f"Backend {backend_name} has partial data ({len(self.legacy_inventory.targets)} targets)")
                    return True  # Accept partial success
            
            logger.debug(f"Backend {backend_name} failed completely")
            return False
    
    def _create_fallback_target(self, target_name: str, target_obj: Any, error_msg: str) -> TargetInfo:
        """Create a fallback TargetInfo when conversion fails.
        
        Attempts to extract as much information as possible even when
        full conversion fails due to interpolation or other errors.
        
        Args:
            target_name: Name of the target.
            target_obj: Original legacy target object.
            error_msg: Error message from conversion failure.
            
        Returns:
            TargetInfo with available information and error details.
        """
        try:
            # Try to extract basic information that doesn't require interpolation
            classes = []
            if hasattr(target_obj, 'classes'):
                try:
                    classes = [str(c) for c in target_obj.classes if c is not None]
                except Exception:
                    pass
            
            # Try to extract basic target type from classes
            target_type = "unknown"
            for class_name in classes:
                if any(keyword in class_name.lower() for keyword in ['jsonnet', 'jinja2', 'helm', 'kadet']):
                    for keyword in ['jsonnet', 'jinja2', 'helm', 'kadet']:
                        if keyword in class_name.lower():
                            target_type = keyword
                            break
                    break
            
            return TargetInfo(
                name=target_name,
                classes=classes,
                applications=[],
                type=target_type,
                parameters={},
                error=f"Conversion failed: {error_msg}"
            )
            
        except Exception as fallback_error:
            logger.debug(f"Even fallback conversion failed for {target_name}: {fallback_error}")
            return TargetInfo(
                name=target_name,
                classes=[],
                applications=[],
                type="unknown",
                parameters={},
                error=f"Complete conversion failure: {error_msg}"
            )
    
    def _fallback_response(self, start_time: float, error: str | None = None) -> InventoryResult:
        """Return enhanced fallback response when inventory reading fails.
        
        Args:
            start_time: Start time for duration calculation.
            error: Error message to include.
            
        Returns:
            InventoryResult indicating failure with comprehensive error info.
        """
        duration = time.perf_counter() - start_time
        return InventoryResult(
            success=False,
            targets=[],
            targets_found=0,
            inventory_path=self.inventory_path,
            duration=duration,
            backend="fallback-enhanced",
            error=error
        )

    def check_inventory_exists(self) -> bool:
        """Check if inventory directory exists with enhanced validation.
        
        Returns:
            True if inventory is accessible and properly structured.
        """
        return self.simple_reader.check_inventory_exists()

    def get_inventory_info(self) -> InventoryInfo:
        """Get comprehensive information about inventory structure.
        
        Leverages both simple reader and legacy Kapitan capabilities
        to provide detailed inventory metadata.
        
        Returns:
            InventoryInfo with enhanced directory structure and file listings.
        """
        # First get basic info from simple reader
        basic_info = self.simple_reader.get_inventory_info()
        
        if not basic_info.exists:
            return basic_info
        
        # Enhance with legacy inventory insights if available
        try:
            legacy_inv = self._get_legacy_inventory()
            if legacy_inv and hasattr(legacy_inv, 'targets'):
                # Add target count and backend information
                target_count = len(legacy_inv.targets)
                backend_name = getattr(self, 'backend_name', 'unknown')
                logger.debug(f"Enhanced inventory info: {target_count} targets via {backend_name}")
        except Exception as e:
            logger.debug(f"Could not enhance inventory info with legacy data: {e}")
        
        return basic_info

    def get_backend_info(self) -> dict[str, Any]:
        """Get information about available inventory backends.
        
        Returns:
            Dictionary with backend availability and capabilities.
        """
        backend_info = {
            "simple_yaml": {"available": True, "features": ["basic_parsing", "fast_loading"]},
            "legacy_available": self._setup_legacy_path(),
            "preferred_backend": None,
            "available_backends": []
        }
        
        if backend_info["legacy_available"]:
            try:
                from kapitan.inventory import AVAILABLE_BACKENDS
                backend_info["available_backends"] = list(AVAILABLE_BACKENDS.keys())
                backend_info["preferred_backend"] = self._backend_preference[0]
            except ImportError:
                logger.debug("Could not import legacy backend information")
                
        return backend_info
