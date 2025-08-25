#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Target resolution utilities for Kapitan."""

import glob
import logging
import os

from pydantic import ValidationError

from .validation import validate_inventory_path

logger = logging.getLogger(__name__)


class TargetResolver:
    """Resolves target patterns to actual target names."""

    def __init__(self, inventory_path: str):
        # Validate inventory path on initialization
        try:
            self.inventory_info = validate_inventory_path(inventory_path)
            self.inventory_path = inventory_path
            self.targets_dir = str(self.inventory_info.targets_dir.path) if self.inventory_info.targets_dir else os.path.join(inventory_path, "targets")
        except ValidationError as e:
            logger.warning(f"Invalid inventory path {inventory_path}: {e}")
            # Fall back to basic path handling for compatibility
            self.inventory_info = None
            self.inventory_path = inventory_path
            self.targets_dir = os.path.join(inventory_path, "targets")

    def resolve_targets(self, target_patterns: list[str]) -> list[str]:
        """
        Resolve target patterns to actual target names.

        Supports:
        - Direct target names: webapp-frontend
        - Directory patterns: inventory/targets/infra/*
        - File patterns: inventory/targets/infra/*.yml
        - Relative paths: infra/apps, gcp/project
        """
        if not target_patterns:
            return ["all"]

        resolved_targets: set[str] = set()

        for pattern in target_patterns:
            targets = self._resolve_single_pattern(pattern)
            resolved_targets.update(targets)

        result = list(resolved_targets)
        logger.debug(f"Resolved patterns {target_patterns} to targets: {result}")
        return result

    def _resolve_single_pattern(self, pattern: str) -> list[str]:
        """Resolve a single target pattern."""
        # If it's just a target name (no path separators), return as-is
        if "/" not in pattern and "*" not in pattern and "?" not in pattern:
            return [pattern]

        # Handle different pattern types
        if self._is_file_pattern(pattern):
            return self._resolve_file_pattern(pattern)
        elif self._is_directory_pattern(pattern):
            return self._resolve_directory_pattern(pattern)
        else:
            # Treat as relative target path
            return self._resolve_relative_target(pattern)

    def _is_file_pattern(self, pattern: str) -> bool:
        """Check if pattern looks like a file pattern."""
        return ("*" in pattern or "?" in pattern) and any(
            pattern.endswith(ext) for ext in [".yml", ".yaml", ".json"]
        )

    def _is_directory_pattern(self, pattern: str) -> bool:
        """Check if pattern looks like a directory pattern."""
        return "*" in pattern or "?" in pattern

    def _resolve_file_pattern(self, pattern: str) -> list[str]:
        """Resolve file patterns like inventory/targets/infra/*.yml"""
        resolved_files = []

        # Handle absolute patterns
        if os.path.isabs(pattern):
            files = glob.glob(pattern)
        else:
            # Try relative to current directory
            files = glob.glob(pattern)
            if not files:
                # Try relative to targets directory
                targets_pattern = os.path.join(self.targets_dir, pattern)
                files = glob.glob(targets_pattern)

        for file_path in files:
            target_name = self._file_to_target_name(file_path)
            if target_name:
                resolved_files.append(target_name)

        return resolved_files

    def _resolve_directory_pattern(self, pattern: str) -> list[str]:
        """Resolve directory patterns like inventory/targets/infra/* or infra/*"""
        resolved_targets = []

        # Handle absolute patterns
        if os.path.isabs(pattern):
            paths = glob.glob(pattern)
        else:
            # Try relative to current directory
            paths = glob.glob(pattern)
            if not paths:
                # Try relative to targets directory
                targets_pattern = os.path.join(self.targets_dir, pattern)
                paths = glob.glob(targets_pattern)

        for path in paths:
            if os.path.isdir(path):
                # Find target files in this directory
                target_files = []
                for ext in [".yml", ".yaml", ".json"]:
                    target_files.extend(glob.glob(os.path.join(path, f"*{ext}")))

                for file_path in target_files:
                    target_name = self._file_to_target_name(file_path)
                    if target_name:
                        resolved_targets.append(target_name)
            elif os.path.isfile(path):
                # It's a file matching the pattern
                target_name = self._file_to_target_name(path)
                if target_name:
                    resolved_targets.append(target_name)

        return resolved_targets

    def _resolve_relative_target(self, pattern: str) -> list[str]:
        """Resolve relative target paths like infra/apps or gcp/project."""
        # Convert relative path to target name
        target_name = pattern.replace("/", ".")

        # Check if this target exists
        possible_paths = [
            os.path.join(self.targets_dir, f"{pattern}.yml"),
            os.path.join(self.targets_dir, f"{pattern}.yaml"),
            os.path.join(self.targets_dir, pattern, f"{os.path.basename(pattern)}.yml"),
            os.path.join(self.targets_dir, pattern, f"{os.path.basename(pattern)}.yaml"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return [target_name]

        # If no exact match, treat as literal target name
        logger.warning(f"Target path '{pattern}' not found, using as literal target name")
        return [target_name]

    def _file_to_target_name(self, file_path: str) -> str | None:
        """Convert a file path to a target name."""
        try:
            # Get relative path from targets directory
            rel_path = os.path.relpath(file_path, self.targets_dir)

            # Remove extension
            name_without_ext = os.path.splitext(rel_path)[0]

            # Convert path separators to dots
            target_name = name_without_ext.replace(os.sep, ".")

            # Handle special case where file is in a directory with same name
            # e.g., targets/infra/apps/apps.yml -> infra.apps (not infra.apps.apps)
            parts = target_name.split(".")
            if len(parts) > 1 and parts[-1] == parts[-2]:
                target_name = ".".join(parts[:-1])

            return target_name

        except Exception as e:
            logger.warning(f"Could not convert file path '{file_path}' to target name: {e}")
            return None

    def list_available_targets(self) -> list[str]:
        """List all available targets in the inventory."""
        targets = []

        if not os.path.exists(self.targets_dir):
            return targets

        # Walk through targets directory
        for root, _dirs, files in os.walk(self.targets_dir):
            for file in files:
                if file.endswith(('.yml', '.yaml', '.json')):
                    file_path = os.path.join(root, file)
                    target_name = self._file_to_target_name(file_path)
                    if target_name:
                        targets.append(target_name)

        return sorted(targets)
