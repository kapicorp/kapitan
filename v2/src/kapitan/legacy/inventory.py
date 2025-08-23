"""Legacy Kapitan inventory integration."""

import logging
import os
import sys
import time
from typing import Dict, List, Optional

from .simple_reader import SimpleInventoryReader

logger = logging.getLogger(__name__)


class LegacyInventoryReader:
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
            # Insert at the beginning to prioritize legacy kapitan
            sys.path.insert(0, legacy_path)
            
        # Also remove our own src path temporarily to avoid conflicts
        v2_path = "/home/coder/kapitan/v2/src"
        if v2_path in sys.path:
            sys.path.remove(v2_path)
            # We'll add it back after import
    
    def _get_legacy_inventory(self):
        """Initialize legacy Kapitan inventory if not already done."""
        if self.legacy_inventory is not None:
            return self.legacy_inventory
            
        try:
            # Store current path and modules
            original_path = sys.path.copy()
            modules_to_restore = {}
            
            # Remove conflicting modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('kapitan.inventory'):
                    modules_to_restore[module_name] = sys.modules.pop(module_name)
            
            # Setup legacy path
            legacy_path = "/home/coder/kapitan"
            sys.path.insert(0, legacy_path)
            
            # Import legacy Kapitan inventory directly
            import importlib.util
            
            # Load the legacy inventory module directly
            inventory_init_path = os.path.join(legacy_path, "kapitan", "inventory", "__init__.py")
            spec = importlib.util.spec_from_file_location("legacy_kapitan_inventory", inventory_init_path)
            legacy_inventory_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(legacy_inventory_module)
            
            # Create inventory backend (using reclass as default)
            inventory_class = legacy_inventory_module.get_inventory_backend("reclass")
            self.legacy_inventory = inventory_class(
                inventory_path=self.inventory_path,
                compose_target_name=False
            )
            
            # Restore original path and modules
            sys.path[:] = original_path
            sys.modules.update(modules_to_restore)
            
            return self.legacy_inventory
            
        except Exception as e:
            logger.error(f"Failed to initialize legacy inventory: {e}")
            # Always restore original state
            try:
                sys.path[:] = original_path
                sys.modules.update(modules_to_restore)
            except:
                pass
            return None
    
    def read_targets(self, target_filter: Optional[List[str]] = None) -> Dict:
        """Read targets from inventory with timing."""
        start_time = time.time()
        
        # First try the simple YAML reader
        try:
            result = self.simple_reader.read_targets(target_filter)
            if result["success"] and result["targets_found"] > 0:
                logger.info(f"Successfully loaded {result['targets_found']} targets using simple YAML reader")
                return result
        except Exception as e:
            logger.debug(f"Simple reader failed: {e}")
        
        # Skip legacy system for now due to dependency conflicts
        # Instead, return fallback response with better error messaging
        logger.info("No valid inventory found, using fallback mock data")
        return self._fallback_response(start_time, error="No inventory found or readable")
    
    def _convert_target(self, target_name: str, target_obj) -> Dict:
        """Convert legacy target object to our format."""
        try:
            # Extract basic information
            target_info = {
                "name": target_name,
                "classes": [],
                "parameters": {},
                "applications": [],
                "type": "unknown"
            }
            
            # Get classes if available
            if hasattr(target_obj, 'classes'):
                target_info["classes"] = list(target_obj.classes) if target_obj.classes else []
            
            # Get applications/parameters if available
            if hasattr(target_obj, 'parameters'):
                if hasattr(target_obj.parameters, 'kapitan'):
                    kapitan_params = target_obj.parameters.kapitan
                    
                    # Get compile parameters
                    if hasattr(kapitan_params, 'compile') and kapitan_params.compile:
                        compile_targets = kapitan_params.compile
                        for compile_target in compile_targets:
                            if hasattr(compile_target, 'input_type'):
                                target_info["type"] = compile_target.input_type
                            if hasattr(compile_target, 'name'):
                                target_info["applications"].append(compile_target.name)
                
                # Store full parameters for reference
                if hasattr(target_obj.parameters, '__dict__'):
                    target_info["parameters"] = target_obj.parameters.__dict__
            
            return target_info
            
        except Exception as e:
            logger.debug(f"Error converting target {target_name}: {e}")
            return {
                "name": target_name,
                "classes": [],
                "parameters": {},
                "applications": [],
                "type": "unknown",
                "error": str(e)
            }
    
    def _fallback_response(self, start_time: float, error: Optional[str] = None) -> Dict:
        """Return fallback response when legacy inventory fails."""
        duration = time.time() - start_time
        return {
            "success": False,
            "targets": [],
            "targets_found": 0,
            "inventory_path": self.inventory_path,
            "duration": duration,
            "backend": "fallback",
            "error": error
        }
    
    def check_inventory_exists(self) -> bool:
        """Check if inventory directory exists."""
        return self.simple_reader.check_inventory_exists()
    
    def get_inventory_info(self) -> Dict:
        """Get basic information about the inventory structure."""
        if not self.check_inventory_exists():
            return {
                "exists": False,
                "targets_dir": None,
                "classes_dir": None,
                "target_files": [],
                "class_files": []
            }
        
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
        
        return {
            "exists": True,
            "targets_dir": targets_dir,
            "classes_dir": classes_dir,
            "target_files": sorted(target_files),
            "class_files": sorted(class_files)
        }