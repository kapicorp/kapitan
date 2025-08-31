"""Simple YAML-based inventory reader."""

import logging
import os
import time

import yaml

from ..core.inventory import InventoryReader
from ..core.models import InventoryInfo, InventoryResult, TargetInfo

logger = logging.getLogger(__name__)


class SimpleInventoryReader(InventoryReader):
    """Simple inventory reader that directly parses YAML files."""

    def __init__(self, inventory_path: str = "inventory"):
        self.inventory_path = inventory_path
        self.targets_dir = os.path.join(inventory_path, "targets")
        self.classes_dir = os.path.join(inventory_path, "classes")

    def read_targets(self, target_filter: list[str] | None = None) -> InventoryResult:
        """Read targets from inventory YAML files."""
        start_time = time.time()

        if not self.check_inventory_exists():
            logger.debug(f"Inventory directory not found: {self.inventory_path}")
            return self._fallback_response(start_time, "Inventory directory not found")

        try:
            # Read all target files
            targets = []
            target_files = self._get_target_files()

            if not target_files:
                logger.debug(f"No target files found in: {self.targets_dir}")
                return self._fallback_response(start_time, "No target files found")

            logger.debug(f"Found {len(target_files)} target files: {target_files}")

            for target_file in target_files:
                target_name = os.path.splitext(target_file)[0]

                # Skip if filtering and target not in filter
                if target_filter and target_filter != ["all"] and target_name not in target_filter:
                    logger.debug(f"Skipping target {target_name} (not in filter)")
                    continue

                target_path = os.path.join(self.targets_dir, target_file)
                target_data = self._read_target_file(target_path, target_name)
                if target_data:
                    targets.append(target_data)
                    logger.debug(f"Successfully read target: {target_name}")

            duration = time.time() - start_time
            success = len(targets) > 0

            if success:
                logger.debug(f"Successfully loaded {len(targets)} targets")
            else:
                logger.debug("No targets loaded successfully")

            return InventoryResult(
                success=success,
                targets=targets,
                targets_found=len(targets),
                inventory_path=self.inventory_path,
                duration=duration,
                backend="simple-yaml"
            )

        except Exception as e:
            logger.error(f"Error reading simple inventory: {e}")
            return self._fallback_response(start_time, str(e))

    def _read_target_file(self, target_path: str, target_name: str) -> TargetInfo | None:
        """Read a single target YAML file."""
        try:
            with open(target_path) as f:
                data = yaml.safe_load(f)

            if not data:
                return None

            # Extract relevant information
            classes = data.get("classes", [])
            parameters = data.get("parameters", {})
            applications = []
            target_type = "unknown"

            # Try to read class files to get compile information
            compile_info = self._extract_compile_info_from_classes(classes)
            if compile_info:
                target_type = compile_info.get("type", target_type)
                applications.extend(compile_info.get("applications", []))

            # Try to extract compile targets from parameters (direct in target)
            if "kapitan" in parameters and "compile" in parameters["kapitan"]:
                compile_targets = parameters["kapitan"]["compile"]

                # Extract main type from first compile target
                if compile_targets and isinstance(compile_targets[0], dict) and "input_type" in compile_targets[0]:
                    target_type = compile_targets[0]["input_type"]

                # Extract application names from input paths
                for compile_target in compile_targets:
                    if isinstance(compile_target, dict) and "input_paths" in compile_target:
                        for input_path in compile_target["input_paths"]:
                            # Extract component name from path like "components/mysql/main.jsonnet"
                            if "/" in input_path and input_path.startswith("components/"):
                                parts = input_path.split("/")
                                if len(parts) > 1 and parts[1] not in applications:
                                    applications.append(parts[1])

            return TargetInfo(
                name=target_name,
                classes=classes,
                parameters=parameters,
                applications=applications,
                type=target_type
            )

        except Exception as e:
            logger.debug(f"Error reading target file {target_path}: {e}")
            return TargetInfo(
                name=target_name,
                classes=[],
                parameters={},
                applications=[],
                type="yaml",
                error=str(e)
            )

    def _extract_compile_info_from_classes(self, classes: list[str]) -> dict:
        """Try to extract compile information from class files."""
        compile_info = {
            "type": "unknown",
            "applications": [],
            "compile_targets": []
        }

        for class_name in classes:
            class_file = self._find_class_file(class_name)
            if class_file:
                try:
                    with open(class_file) as f:
                        class_data = yaml.safe_load(f)

                    if class_data and "parameters" in class_data:
                        params = class_data["parameters"]
                        if "kapitan" in params and "compile" in params["kapitan"]:
                            compile_targets = params["kapitan"]["compile"]
                            compile_info["compile_targets"].extend(compile_targets)

                            # Extract type from first compile target
                            if compile_targets and isinstance(compile_targets[0], dict) and "input_type" in compile_targets[0]:
                                compile_info["type"] = compile_targets[0]["input_type"]

                            # Extract applications from input paths
                            for compile_target in compile_targets:
                                if isinstance(compile_target, dict) and "input_paths" in compile_target:
                                    for input_path in compile_target["input_paths"]:
                                        if "/" in input_path and input_path.startswith("components/"):
                                            parts = input_path.split("/")
                                            if len(parts) > 1 and parts[1] not in compile_info["applications"]:
                                                compile_info["applications"].append(parts[1])

                except Exception as e:
                    logger.debug(f"Error reading class file {class_file}: {e}")

        return compile_info

    def _find_class_file(self, class_name: str) -> str | None:
        """Find the YAML file for a given class name."""
        if not os.path.exists(self.classes_dir):
            return None

        # Try different possible file patterns
        possible_files = [
            f"{class_name}.yml",
            f"{class_name}.yaml",
        ]

        # Also try nested structure (e.g., component/mysql.yml for component.mysql)
        if "." in class_name:
            parts = class_name.split(".")
            nested_path = "/".join(parts) + ".yml"
            possible_files.append(nested_path)
            nested_path_yaml = "/".join(parts) + ".yaml"
            possible_files.append(nested_path_yaml)

        for possible_file in possible_files:
            full_path = os.path.join(self.classes_dir, possible_file)
            if os.path.exists(full_path):
                return full_path

        return None

    def _get_target_files(self) -> list[str]:
        """Get list of target YAML files."""
        if not os.path.exists(self.targets_dir):
            return []

        try:
            files = []
            for f in os.listdir(self.targets_dir):
                if f.endswith('.yml') or f.endswith('.yaml'):
                    files.append(f)
            return sorted(files)
        except Exception as e:
            logger.debug(f"Error listing target files: {e}")
            return []

    def check_inventory_exists(self) -> bool:
        """Check if inventory directory exists."""
        return (os.path.exists(self.inventory_path) and
                os.path.isdir(self.inventory_path) and
                os.path.exists(self.targets_dir))

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

        target_files = self._get_target_files()
        class_files = []

        try:
            if os.path.exists(self.classes_dir):
                class_files = [f for f in os.listdir(self.classes_dir)
                              if f.endswith('.yml') or f.endswith('.yaml')]
                class_files.sort()
        except Exception as e:
            logger.debug(f"Error reading classes directory: {e}")

        return InventoryInfo(
            exists=True,
            targets_dir=self.targets_dir,
            classes_dir=self.classes_dir,
            target_files=sorted(target_files),
            class_files=class_files
        )

    def _fallback_response(self, start_time: float, error: str | None = None) -> InventoryResult:
        """Return fallback response when inventory reading fails."""
        duration = time.time() - start_time
        return InventoryResult(
            success=False,
            targets=[],
            targets_found=0,
            inventory_path=self.inventory_path,
            duration=duration,
            backend="simple-yaml-fallback",
            error=error
        )
