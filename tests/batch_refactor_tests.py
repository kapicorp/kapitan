#!/usr/bin/env python3
"""
Batch refactor test files to use pytest fixtures and best practices.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def refactor_unittest_to_pytest(content: str) -> str:
    """Convert unittest imports and assertions to pytest."""
    # Remove unittest imports
    content = re.sub(r"^import unittest\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^from unittest import.*\n", "", content, flags=re.MULTILINE)

    # Add pytest import if not present
    if "import pytest" not in content:
        # Add after other imports
        lines = content.split("\n")
        import_end = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_end = i + 1
            elif import_end > 0 and line and not line.startswith("#"):
                break
        lines.insert(import_end, "\nimport pytest")
        content = "\n".join(lines)

    # Convert unittest.TestCase to regular class
    content = re.sub(r"class (\w+)\(unittest\.TestCase\):", r"class Test\1:", content)
    content = re.sub(r"class Test(\w+)\(unittest\.TestCase\):", r"class Test\1:", content)

    # Convert assertions
    content = re.sub(r"self\.assertEqual\((.*?),\s*(.*?)\)", r"assert \1 == \2", content)
    content = re.sub(r"self\.assertNotEqual\((.*?),\s*(.*?)\)", r"assert \1 != \2", content)
    content = re.sub(r"self\.assertTrue\((.*?)\)", r"assert \1", content)
    content = re.sub(r"self\.assertFalse\((.*?)\)", r"assert not \1", content)
    content = re.sub(r"self\.assertIsNone\((.*?)\)", r"assert \1 is None", content)
    content = re.sub(r"self\.assertIsNotNone\((.*?)\)", r"assert \1 is not None", content)
    content = re.sub(r"self\.assertIn\((.*?),\s*(.*?)\)", r"assert \1 in \2", content)
    content = re.sub(r"self\.assertNotIn\((.*?),\s*(.*?)\)", r"assert \1 not in \2", content)
    content = re.sub(r"self\.assertRaises\((.*?)\)", r"pytest.raises(\1)", content)
    content = re.sub(r"self\.assertListEqual\((.*?),\s*(.*?)\)", r"assert \1 == \2", content)
    content = re.sub(r"self\.assertDictEqual\((.*?),\s*(.*?)\)", r"assert \1 == \2", content)

    # Remove self parameter from test methods
    content = re.sub(r"def test_(\w+)\(self\):", r"def test_\1():", content)

    return content


def convert_setup_teardown_to_fixtures(content: str) -> str:
    """Convert setUp/tearDown methods to pytest fixtures."""
    lines = content.split("\n")
    new_lines = []
    in_setup = False
    in_teardown = False
    setup_body = []
    teardown_body = []
    indent = "    "

    for line in lines:
        if "def setUp(self):" in line:
            in_setup = True
            continue
        elif "def tearDown(self):" in line:
            in_teardown = True
            continue
        elif in_setup:
            if line and not line.startswith(indent):
                in_setup = False
                # Don't add the setup method
            else:
                setup_body.append(line[len(indent) :] if line.startswith(indent) else line)
                continue
        elif in_teardown:
            if line and not line.startswith(indent):
                in_teardown = False
                # Don't add the teardown method
            else:
                teardown_body.append(line[len(indent) :] if line.startswith(indent) else line)
                continue

        new_lines.append(line)

    # If we found setUp/tearDown, create a fixture
    if setup_body or teardown_body:
        fixture_code = [
            "",
            "@pytest.fixture(autouse=True)",
            "def setup_teardown():",
            '    """Setup and teardown for tests."""',
        ]

        if setup_body:
            fixture_code.append("    # Setup")
            for line in setup_body:
                if line.strip():
                    fixture_code.append("    " + line)

        fixture_code.append("    ")
        fixture_code.append("    yield")
        fixture_code.append("    ")

        if teardown_body:
            fixture_code.append("    # Teardown")
            for line in teardown_body:
                if line.strip():
                    fixture_code.append("    " + line)

        # Insert fixture before the first test class
        for i, line in enumerate(new_lines):
            if line.startswith("class Test"):
                new_lines = new_lines[:i] + fixture_code + [""] + new_lines[i:]
                break

    return "\n".join(new_lines)


def add_fixture_imports(content: str) -> str:
    """Add imports for common fixtures from conftest."""
    if "from conftest import" not in content:
        # Check what fixtures might be needed
        needs_fixtures = []

        if "os.chdir" in content:
            needs_fixtures.append("isolated_compile_dir")
        if "TEST_RESOURCES_PATH" in content or "test_resources" in content:
            needs_fixtures.append("isolated_test_resources")
        if "TEST_KUBERNETES_PATH" in content or "examples/kubernetes" in content:
            needs_fixtures.append("isolated_kubernetes_inventory")
        if "tempfile.mkdtemp" in content:
            needs_fixtures.append("temp_dir")

        if needs_fixtures:
            # Add import after pytest import
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "import pytest" in line:
                    lines.insert(i + 1, f"from conftest import {', '.join(needs_fixtures)}")
                    break
            content = "\n".join(lines)

    return content


def replace_os_chdir_patterns(content: str) -> str:
    """Replace os.chdir patterns with fixture usage."""
    # Pattern: os.chdir(TEST_RESOURCES_PATH)
    content = re.sub(
        r"os\.chdir\(TEST_RESOURCES_PATH\)",
        "# Use isolated_test_resources fixture instead of os.chdir",
        content,
    )

    # Pattern: os.chdir(TEST_KUBERNETES_PATH)
    content = re.sub(
        r"os\.chdir\(TEST_KUBERNETES_PATH\)",
        "# Use isolated_kubernetes_inventory fixture instead of os.chdir",
        content,
    )

    # Pattern: os.chdir(<any_path>)
    content = re.sub(r"os\.chdir\([^)]+\)", "# TODO: Replace os.chdir with isolated fixture", content)

    return content


def replace_shutil_rmtree_patterns(content: str) -> str:
    """Replace shutil.rmtree patterns with temp_dir fixture."""
    content = re.sub(
        r"shutil\.rmtree\([^,)]+,\s*ignore_errors=True\)", "# Cleanup handled by temp_dir fixture", content
    )

    content = re.sub(r"shutil\.rmtree\([^)]+\)", "# TODO: Use temp_dir fixture for cleanup", content)

    return content


def refactor_test_file(filepath: Path) -> bool:
    """Refactor a single test file. Returns True if changes were made."""
    with open(filepath, "r") as f:
        original_content = f.read()

    content = original_content

    # Apply refactoring steps
    content = refactor_unittest_to_pytest(content)
    content = convert_setup_teardown_to_fixtures(content)
    content = add_fixture_imports(content)
    content = replace_os_chdir_patterns(content)
    content = replace_shutil_rmtree_patterns(content)

    # Only write if changes were made
    if content != original_content:
        # Create backup
        backup_path = filepath.with_suffix(".py.backup")
        with open(backup_path, "w") as f:
            f.write(original_content)

        # Write refactored content
        with open(filepath, "w") as f:
            f.write(content)

        return True

    return False


def batch_refactor():
    """Refactor all test files."""
    test_dir = Path(__file__).parent

    # Files to refactor
    files_to_refactor = [
        "test_version.py",  # Start with simple ones
        "test_linter.py",
        "test_kadet.py",
    ]

    print("Starting batch refactoring...")
    print("=" * 60)

    for filename in files_to_refactor:
        filepath = test_dir / filename
        if filepath.exists():
            print(f"Refactoring {filename}...")
            if refactor_test_file(filepath):
                print(f"  ✓ Refactored successfully (backup created)")
            else:
                print(f"  - No changes needed")
        else:
            print(f"  ✗ File not found: {filename}")

    print("=" * 60)
    print("Refactoring complete!")
    print("\nNote: Backup files created with .backup extension")
    print("Manual review and testing is recommended")


if __name__ == "__main__":
    batch_refactor()
