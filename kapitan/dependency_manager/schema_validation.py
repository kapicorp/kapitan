# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Generator schema discovery and validation for Kapitan dependencies."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from jsonschema.validators import validator_for


if TYPE_CHECKING:
    from jsonschema import ValidationError


logger = logging.getLogger(__name__)


class _SourceTrackerCache:
    """Cache _SourceTracker instances by filepath to avoid re-parsing YAML files."""

    def __init__(self):
        self._cache: dict[Path, _SourceTracker] = {}

    def get(self, filepath: Path) -> _SourceTracker:
        if filepath not in self._cache:
            self._cache[filepath] = _SourceTracker(filepath)
        return self._cache[filepath]


def _resolve_schema_path(dep) -> Path | None:
    """Resolve the candidate schema file for a dependency.

    Uses ``schema_path`` if set, otherwise falls back to
    ``<output_path>/schema.json``.  Returns ``None`` if the file does not
    exist.
    """
    if dep.schema_path is not None:
        candidate = Path(dep.schema_path)
    else:
        candidate = Path(dep.output_path) / "schema.json"

    if candidate.is_file():
        return candidate
    return None


def _get_inventory_subtree(parameters: dict, path: str | None):
    """Resolve a dotted inventory path from *parameters*.

    E.g. ``parameters.components.argocd`` walks into the dict and returns
    the value at that key path.  Returns ``None`` when *path* is ``None``
    or any key along the path is missing.
    """
    if path is None:
        return None

    keys = path.split(".")
    value = parameters
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


class _SourceTracker:
    """Scan a YAML file and record dotted key paths mapped to line/column."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.locations: dict[str, tuple[int, int, str]] = {}
        self._scan()

    def _scan(self):
        try:
            with self.filepath.open("r", encoding="utf-8") as fh:
                loader = yaml.SafeLoader(fh)
                try:
                    node = loader.get_single_node()
                finally:
                    loader.dispose()
        except Exception:
            return
        if node is None:
            return
        self._walk(node, [])

    def _walk(self, node, path: list[str]):
        if isinstance(node, yaml.MappingNode):
            for key_node, value_node in node.value:
                key = key_node.value
                new_path = path + [key]
                dotted = ".".join(new_path)
                if isinstance(value_node, yaml.ScalarNode):
                    self.locations[dotted] = (
                        value_node.start_mark.line + 1,
                        value_node.start_mark.column + 1,
                        value_node.value,
                    )
                self._walk(value_node, new_path)
        elif isinstance(node, yaml.SequenceNode):
            for idx, item_node in enumerate(node.value):
                self._walk(item_node, path + [str(idx)])


def _find_source_location(
    full_path: list[str],
    inventory_path: str,
    tracker_cache: _SourceTrackerCache,
) -> dict | None:
    """Search inventory YAML files for the source of *full_path*.

    Returns a dict with ``filepath``, ``line``, ``col``, and ``context``
    (list of ``(lineno, text)`` tuples) or ``None`` when no source can be
    determined.
    """
    dotted = ".".join(full_path)
    # Search targets first (more specific) then classes.
    search_roots = [
        Path(inventory_path) / "targets",
        Path(inventory_path) / "classes",
    ]
    candidate_files: list[Path] = []
    for root in search_roots:
        if not root.is_dir():
            continue
        candidate_files.extend(root.rglob("*.yml"))
        candidate_files.extend(root.rglob("*.yaml"))

    for yaml_file in candidate_files:
        tracker = tracker_cache.get(yaml_file)
        if dotted in tracker.locations:
            line, col, _found_value = tracker.locations[dotted]
            context = _read_context(yaml_file, line)
            return {
                "filepath": str(yaml_file),
                "line": line,
                "col": col,
                "context": context,
            }

    return None


def _read_context(
    filepath: Path, target_line: int, radius: int = 3
) -> list[tuple[int, str]]:
    """Return ``(lineno, text)`` for lines around *target_line* (1-based)."""
    try:
        with filepath.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return []

    result = []
    start = max(0, target_line - radius - 1)
    end = min(len(lines), target_line + radius)
    for i in range(start, end):
        result.append((i + 1, lines[i].rstrip("\n")))
    return result


def _format_validation_error(
    error: ValidationError,
    schema_path: str,
    dependency_output_path: str,
    inventory_dotted_path: str | None,
    inventory_path: str,
    tracker_cache: _SourceTrackerCache,
) -> str:
    """Format a single validation error with source context.

    Returns a compiler-style multi-line message.
    """
    # Error code: E-<dep-name>.<validator>
    dep_name = Path(dependency_output_path).name or "generator"
    validator = error.validator or "validation"
    error_code = f"E-{dep_name}.{validator}"

    # Build the full key path inside the inventory.
    json_path = list(error.path)
    if inventory_dotted_path:
        full_path = inventory_dotted_path.split(".") + json_path
    else:
        full_path = json_path
    key_path = ".".join(full_path) if full_path else "<root>"

    # Human-readable problem.
    problem = error.message

    lines: list[str] = [f"{error_code}", ""]
    lines.append(f"{key_path} must satisfy schema constraint")
    lines.append(f"  Problem: {problem}")
    lines.append(f"  Schema: {schema_path}")

    # Try to locate the source file.
    source = _find_source_location(full_path, inventory_path, tracker_cache)
    if source:
        lines.append("")
        lines.append(f"{source['filepath']}:{source['line']}:{source['col']}")
        lines.append("")

        max_lineno = max(ln for ln, _ in source["context"])
        num_width = len(str(max_lineno))
        for lineno, text in source["context"]:
            prefix = f"{lineno:>{num_width}} |"
            if lineno == source["line"]:
                lines.append(f"> {prefix} {text}")
            else:
                lines.append(f"  {prefix} {text}")

    return "\n".join(lines)


def _validate_against_schema(
    data,
    schema_path: Path,
    dependency_output_path: str,
    inventory_dotted_path: str | None,
    inventory_path: str,
    tracker_cache: _SourceTrackerCache,
) -> list[dict]:
    """Validate *data* against the JSON Schema stored at *schema_path*.

    Returns a list of structured error dicts, each containing
    ``message``, ``validator``, ``path``, and ``formatted``.
    """
    try:
        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [
            {
                "message": f"Failed to load schema from {schema_path}: {e}",
                "validator": "schema-load",
                "path": [],
                "formatted": f"Failed to load schema from {schema_path}: {e}",
            }
        ]

    try:
        ValidatorClass = validator_for(schema)
        ValidatorClass.check_schema(schema)
        validator = ValidatorClass(schema)
    except Exception as e:
        return [
            {
                "message": f"Invalid schema in {schema_path}: {e}",
                "validator": "schema-invalid",
                "path": [],
                "formatted": f"Invalid schema in {schema_path}: {e}",
            }
        ]

    errors = []
    for error in validator.iter_errors(data):
        formatted = _format_validation_error(
            error,
            str(schema_path),
            dependency_output_path,
            inventory_dotted_path,
            inventory_path,
            tracker_cache,
        )
        errors.append(
            {
                "message": error.message,
                "validator": error.validator or "validation",
                "path": list(error.path),
                "formatted": formatted,
            }
        )
    return errors


def validate_generator_schemas(
    target_obj,
    parameters: dict,
    inventory_path: str,
    tracker_cache: _SourceTrackerCache | None = None,
) -> list[dict]:
    """Validate generator schemas for a single target.

    Iterates over the target's dependencies, discovers any schema files,
    extracts the configured inventory subtree, and validates it.

    *target_obj* is the target's ``KapitanInventorySettings`` (which holds
    ``dependencies``).  *parameters* is the full merged ``parameters`` dict
    for the target.  *inventory_path* is the root inventory directory used
    to resolve source file locations.

    Returns a list of finding dicts, each with keys:
    ``dependency``, ``schema_path``, ``inventory_path``, ``errors``.
    """
    if tracker_cache is None:
        tracker_cache = _SourceTrackerCache()

    findings = []

    for dep in target_obj.dependencies or []:
        schema_path = _resolve_schema_path(dep)
        if schema_path is None:
            continue

        inventory_dotted_path = dep.schema_inventory_path
        data = _get_inventory_subtree(parameters, inventory_dotted_path)
        if data is None:
            if inventory_dotted_path is not None:
                logger.warning(
                    "Schema %s exists but inventory path %r does not resolve; skipping validation",
                    schema_path,
                    inventory_dotted_path,
                )
            continue

        errors = _validate_against_schema(
            data,
            schema_path,
            dep.output_path,
            inventory_dotted_path,
            inventory_path,
            tracker_cache,
        )
        if errors:
            findings.append(
                {
                    "dependency": dep.output_path,
                    "schema_path": str(schema_path),
                    "inventory_path": inventory_dotted_path,
                    "errors": errors,
                }
            )

    return findings
